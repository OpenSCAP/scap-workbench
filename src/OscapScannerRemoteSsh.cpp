/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "OscapScannerRemoteSsh.h"
#include "Exceptions.h"
#include "ScanningSession.h"

#include <QThread>
#include <QAbstractEventDispatcher>
#include <QTemporaryFile>
#include <QFileInfo>
#include <QDir>
#include <cassert>

extern "C"
{
#include <xccdf_session.h>
#include <xccdf_benchmark.h>
}

OscapScannerRemoteSsh::OscapScannerRemoteSsh():
    OscapScannerBase(),
    mSshConnection(this)
{
    mSshConnection.setCancelRequestSource(&mCancelRequested);
}

OscapScannerRemoteSsh::~OscapScannerRemoteSsh()
{}

inline void splitTarget(const QString& in, QString& target, short& port)
{
    // NB: We dodge a bullet here because the editor will always pass a port
    //     as the last component. A lot of checking and parsing does not need
    //     to be done.
    //
    //     'in' is in the format of username@hostname:port, the port always
    //     being there and always being the last component.

    // FIXME: Ideally, this should split from the right side and stop after one split
    QStringList split = in.split(':');

    const QString portString = split.back();
    split.removeLast();

    {
        bool status = false;
        const short portCandidate = portString.toShort(&status, 10);

        // FIXME: Error reporting?
        port = status ? portCandidate : 22;
    }

    target = split.join(":");
}

void OscapScannerRemoteSsh::setTarget(const QString& target)
{
    OscapScannerBase::setTarget(target);

    if (mSshConnection.isConnected())
        mSshConnection.disconnect();

    QString cleanTarget;
    short port;

    splitTarget(target, cleanTarget, port);

    mSshConnection.setTarget(cleanTarget);
    mSshConnection.setPort(port);
}

void OscapScannerRemoteSsh::setSession(ScanningSession* session)
{
    OscapScannerBase::setSession(session);

    if (!mSession->isSDS())
        throw OscapScannerRemoteSshException("You can only use source datastreams for scanning remotely!");
}

void OscapScannerRemoteSsh::evaluate()
{
    ensureConnected();

    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

    emit infoMessage("Querying capabilities on remote machine...");

    {
        SshSyncProcess proc(mSshConnection, this);
        proc.setCommand(SCAP_WORKBENCH_REMOTE_OSCAP_PATH);
        proc.setArguments(QStringList("--v"));
        proc.setCancelRequestSource(&mCancelRequested);
        proc.run();

        if (proc.getExitCode() != 0)
        {
            emit errorMessage(
                QString("Failed to query capabilities of oscap on local machine.\n"
                        "Diagnostic info:\n%1").arg(proc.getDiagnosticInfo())
            );

            mCancelRequested = true;
            signalCompletion(mCancelRequested);
            return;
        }

        mCapabilities.parse(proc.getStdOutContents());
    }

    if (!checkPrerequisites())
    {
        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return;
    }

    QStringList baseArgs;
    baseArgs.append("-o"); baseArgs.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));
    baseArgs.append(mTarget);

    QString diagnosticInfo;

    emit infoMessage("Copying input data to remote target...");

    const QString inputFile = copyInputFileOver();
    const QString tailoringFile = mSession->hasTailoring() ?
        copyFileOver(mSession->getTailoringFilePath()) : QString();

    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

    const QString reportFile = createRemoteTemporaryFile();
    const QString resultFile = createRemoteTemporaryFile();
    const QString arfFile = createRemoteTemporaryFile();
    const QString workingDir = createRemoteTemporaryDirectory();

    // TODO: We could be leaking any of the temporary files at this point!
    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

    QStringList args;

    if (mScannerMode == SM_OFFLINE_REMEDIATION)
    {
        args = buildOfflineRemediationArgs(inputFile,
                resultFile,
                reportFile,
                arfFile);
    }
    else
    {
        args = buildEvaluationArgs(inputFile,
                tailoringFile,
                resultFile,
                reportFile,
                arfFile,
                mScannerMode == SM_SCAN_ONLINE_REMEDIATION);
    }

    const QString sshCmd = args.join(" ");

    emit infoMessage("Starting the remote process...");
    QProcess process(this);
    process.start("ssh", baseArgs + QStringList(QString("cd '%1'; " SCAP_WORKBENCH_REMOTE_OSCAP_PATH " %2").arg(workingDir).arg(sshCmd)));

    const unsigned int pollInterval = 100;

    emit infoMessage("Processing on the remote machine...");
    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        readStdOut(process);
        watchStdErr(process);

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mScanThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            emit infoMessage("Cancelation was requested! Terminating...");
            // TODO: On Windows we have to kill immediately, terminate() posts WM_CLOSE
            //       but oscap doesn't have any event loop running.
            process.terminate();
            break;
        }
    }

    if (mCancelRequested)
    {
        unsigned int waited = 0;
        while (!process.waitForFinished(pollInterval))
        {
            waited += pollInterval;
            if (waited > 10000) // 10 seconds should be enough for the process to terminate
            {
                emit warningMessage("The oscap process didn't terminate in time, it will be killed instead.");
                // if it didn't terminate, we have to kill it at this point
                process.kill();
                break;
            }
        }
    }
    else
    {
        // read everything left over
        readStdOut(process);
        watchStdErr(process);

        mResults = readRemoteFile(resultFile, "XCCDF results").toUtf8();
        mReport = readRemoteFile(reportFile, "XCCDF report (HTML)").toUtf8();
        mARF = readRemoteFile(arfFile, "Result DataStream (ARF)").toUtf8();
    }

    emit infoMessage("Cleaning up...");

    // Remove all the temporary remote files
    removeRemoteFile(inputFile, "input file");
    if (!tailoringFile.isEmpty())
        removeRemoteFile(tailoringFile, "tailoring file");
    removeRemoteFile(resultFile, "XCCDF result file");
    removeRemoteFile(reportFile, "XCCDF report file");
    removeRemoteFile(arfFile, "Result DataStream file");
    removeRemoteDirectory(workingDir, "Temporary Working Directory");

    emit infoMessage("Processing has been finished!");
    signalCompletion(mCancelRequested);
}

void OscapScannerRemoteSsh::ensureConnected()
{
    if (mSshConnection.isConnected())
        return;

    try
    {
        emit infoMessage("Establishing connecting to remote target...");
        mSshConnection.connect();
        emit infoMessage("Connection established.");
    }
    catch(const SshConnectionException& e)
    {
        emit errorMessage("Can't connect to remote machine! Exception was: " + QString::fromUtf8(e.what()));
        mCancelRequested = true;
    }
}

QString OscapScannerRemoteSsh::copyFileOver(const QString& localPath)
{
    ensureConnected();

    QString ret = createRemoteTemporaryFile();

    {
        ScpSyncProcess proc(mSshConnection, this);
        proc.setDirection(SD_LOCAL_TO_REMOTE);
        proc.setLocalPath(localPath);
        proc.setRemotePath(ret);
        proc.setCancelRequestSource(&mCancelRequested);

        proc.run();

        if (proc.getExitCode() != 0)
        {
            emit errorMessage(
                QString("Failed to copy '%1' over to the remote machine! "
                        "Diagnostic info:\n%1").arg(localPath).arg(proc.getDiagnosticInfo())
            );

            mCancelRequested = true;
        }
    }

    return ret;
}

QString OscapScannerRemoteSsh::copyInputFileOver()
{
    ensureConnected();

    QString localPath = "";

    QTemporaryFile inputARFFile;
    inputARFFile.setAutoRemove(true);
    if (mScannerMode == SM_OFFLINE_REMEDIATION)
    {
        inputARFFile.open();
        inputARFFile.write(getARFForRemediation());
        inputARFFile.close();

        localPath = inputARFFile.fileName();
    }
    else
    {
        localPath = mSession->getOpenedFilePath();
    }

    return copyFileOver(localPath);
}

QString OscapScannerRemoteSsh::createRemoteTemporaryFile(bool cancelOnFailure)
{
    ensureConnected();

    SshSyncProcess proc(mSshConnection, this);
    proc.setCommand("mktemp");
    proc.setCancelRequestSource(&mCancelRequested);
    proc.run();

    if (proc.getExitCode() != 0)
    {
        emit errorMessage(
            QString("Failed to create a valid temporary file to copy input "
                    "data to! Diagnostic info: %1").arg(proc.getDiagnosticInfo())
        );

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return "";
    }

    return proc.getStdOutContents().trimmed();
}

QString OscapScannerRemoteSsh::createRemoteTemporaryDirectory(bool cancelOnFailure)
{
    ensureConnected();

    SshSyncProcess proc(mSshConnection, this);
    proc.setCommand("mktemp");
    proc.setArguments(QStringList("-d"));
    proc.setCancelRequestSource(&mCancelRequested);
    proc.run();

    if (proc.getExitCode() != 0)
    {
        emit errorMessage(
            QString("Failed to create a valid temporary dir. "
                    "Diagnostic info: %1").arg(proc.getDiagnosticInfo())
        );

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return "";
    }

    return proc.getStdOutContents().trimmed();
}

QString OscapScannerRemoteSsh::readRemoteFile(const QString& path, const QString& desc)
{
    SshSyncProcess proc(mSshConnection, this);
    proc.setCommand("cat");
    proc.setArguments(QStringList(path));
    proc.setCancelRequestSource(&mCancelRequested);
    proc.run();

    if (proc.getExitCode() != 0)
    {
        emit warningMessage(QString(
            "Failed to copy back %1. "
            "You will not be able to save this data! Diagnostic info: %2").arg(desc).arg(proc.getDiagnosticInfo()));

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return "";
    }

    return proc.getStdOutContents();
}

void OscapScannerRemoteSsh::removeRemoteFile(const QString& path, const QString& desc)
{
    SshSyncProcess proc(mSshConnection, this);
    proc.setCommand("rm");
    proc.setArguments(QStringList(path));
    proc.setCancelRequestSource(&mCancelRequested);
    proc.run();

    if (proc.getExitCode() != 0)
    {
        emit warningMessage(QString(
            "Failed to remote remote file %1. "
            "Diagnostic info: %2").arg(desc).arg(proc.getDiagnosticInfo()));

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
    }
}

void OscapScannerRemoteSsh::removeRemoteDirectory(const QString& path, const QString& desc)
{
    SshSyncProcess proc(mSshConnection, this);
    proc.setCommand("rm");
    QStringList args;
    args.push_back("-rf"); args.push_back(path);
    proc.setArguments(args);
    proc.setCancelRequestSource(&mCancelRequested);
    proc.run();

    if (proc.getExitCode() != 0)
    {
        emit warningMessage(QString(
            "Failed to remote remote directory %1. "
            "Diagnostic info: %2").arg(desc).arg(proc.getDiagnosticInfo()));

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
    }
}
