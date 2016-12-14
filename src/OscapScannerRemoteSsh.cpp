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

void OscapScannerRemoteSsh::splitTarget(const QString& in, QString& target, short& port)
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
        throw OscapScannerRemoteSshException("You can only use source datastreams for scanning remotely! "
            "Remote scanning using plain XCCDF and OVAL files has not been implemented in SCAP Workbench yet.");
}

QStringList OscapScannerRemoteSsh::getCommandLineArgs() const
{
    QStringList args("oscap-ssh");
    args.append(mSshConnection.getTarget());
    args.append(QString::number(mSshConnection.getPort()));

    if (mScannerMode == SM_OFFLINE_REMEDIATION)
    {
        QTemporaryFile inputARFFile;
        inputARFFile.setAutoRemove(true);
        inputARFFile.open();
        inputARFFile.write(getARFForRemediation());
        inputARFFile.close();

        args += buildOfflineRemediationArgs(inputARFFile.fileName(),
            "/tmp/xccdf-results.xml",
            "/tmp/report.html",
            "/tmp/arf.xml",
            // ignore capabilities because of dry-run
            true
        );
    }
    else
    {
        args += buildEvaluationArgs(mSession->getOpenedFilePath(),
            mSession->getUserTailoringFilePath(),
            "/tmp/xccdf-results.xml",
            "/tmp/report.html",
            "/tmp/arf.xml",
            mScannerMode == SM_SCAN_ONLINE_REMEDIATION,
            // ignore capabilities because of dry-run
            true
        );
    }

    args.removeOne("--progress");

    return args;
}

void OscapScannerRemoteSsh::evaluate()
{
    if (mDryRun)
    {
        signalCompletion(mCancelRequested);
        return;
    }

    ensureConnected();

    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

    {
        SshSyncProcess proc(mSshConnection, this);
        emit infoMessage(QObject::tr("Checking if oscap is available on remote machine..."));

        proc.setCommand(QString("command"));
        proc.setArguments(QStringList() << "-v" << SCAP_WORKBENCH_REMOTE_OSCAP_PATH);
        proc.setCancelRequestSource(&mCancelRequested);
        proc.run();

        if (proc.getExitCode() != 0)
        {
            emit errorMessage(
                QObject::tr("Failed to locate oscap on remote machine. "
                        "Please, check that openscap-scanner is installed on the remote machine.")
            );

            mCancelRequested = true;
            signalCompletion(mCancelRequested);
            return;
        }

        emit infoMessage(QObject::tr("Querying capabilities on remote machine..."));
        proc.setCommand(SCAP_WORKBENCH_REMOTE_OSCAP_PATH);
        proc.setArguments(QStringList("-V"));
        proc.setCancelRequestSource(&mCancelRequested);
        proc.run();

        if (proc.getExitCode() != 0)
        {
            emit errorMessage(
                QObject::tr("Failed to query capabilities of oscap on remote machine.\n"
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

    emit infoMessage(QObject::tr("Copying input data to remote target..."));

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

    emit infoMessage(QObject::tr("Starting the remote process..."));

    QProcess process(this);

    process.start(SCAP_WORKBENCH_LOCAL_SSH_PATH, baseArgs + QStringList(QString("cd '%1'; " SCAP_WORKBENCH_REMOTE_OSCAP_PATH " %2").arg(workingDir).arg(sshCmd)));
    process.waitForStarted();

    if (process.state() != QProcess::Running)
    {
        emit errorMessage(QObject::tr("Failed to start ssh. Perhaps the executable was not found?"));
        mCancelRequested = true;
    }

    const unsigned int pollInterval = 100;

    emit infoMessage(QObject::tr("Processing on the remote machine..."));
    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        readStdOut(process);
        watchStdErr(process);

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mScanThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            emit infoMessage(QObject::tr("Cancellation was requested! Terminating..."));
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
                emit warningMessage(QObject::tr("The oscap process didn't terminate in time, it will be killed instead."));
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

        mResults = readRemoteFile(resultFile, QObject::tr("XCCDF results")).toUtf8();
        mReport = readRemoteFile(reportFile, QObject::tr("XCCDF report (HTML)")).toUtf8();
        mARF = readRemoteFile(arfFile, QObject::tr("Result DataStream (ARF)")).toUtf8();
    }

    emit infoMessage(QObject::tr("Cleaning up..."));

    // Remove all the temporary remote files
    removeRemoteFile(inputFile, QObject::tr("input file"));
    if (!tailoringFile.isEmpty())
        removeRemoteFile(tailoringFile, QObject::tr("tailoring file"));
    removeRemoteFile(resultFile, QObject::tr("XCCDF result file"));
    removeRemoteFile(reportFile, QObject::tr("XCCDF report file"));
    removeRemoteFile(arfFile, QObject::tr("Result DataStream file"));
    removeRemoteDirectory(workingDir, QObject::tr("Temporary Working Directory"));

    emit infoMessage(QObject::tr("Processing has been finished!"));
    signalCompletion(mCancelRequested);
}

void OscapScannerRemoteSsh::ensureConnected()
{
    if (mSshConnection.isConnected())
        return;

    try
    {
        emit infoMessage(QObject::tr("Establishing connecting to remote target..."));
        mSshConnection.connect();
        emit infoMessage(QObject::tr("Connection established."));
    }
    catch(const SshConnectionException& e)
    {
        emit errorMessage(QObject::tr("Can't connect to remote machine! Exception was: %1").arg(QString::fromUtf8(e.what())));
        mCancelRequested = true;
    }
}

QString OscapScannerRemoteSsh::copyFileOver(const QString& localPath)
{
    ensureConnected();

    QString ret = createRemoteTemporaryFile();

    {
        SshSyncProcess proc(mSshConnection, this);
        proc.setStdInFile(localPath);
        proc.setCommand("tee");
        proc.setArguments(QStringList(ret));
        proc.setCancelRequestSource(&mCancelRequested);
        proc.run();

        if (proc.getExitCode() != 0)
        {
            emit errorMessage(
                QObject::tr("Failed to copy '%1' over to the remote machine! "
                            "Diagnostic info:\n%2").arg(localPath).arg(proc.getDiagnosticInfo())
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
            QObject::tr("Failed to create a valid temporary file to copy input "
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
            QObject::tr("Failed to create a valid temporary dir. "
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
            QObject::tr("Failed to copy back %1. "
            "You will not be able to save this data! Diagnostic info: %2")).arg(desc).arg(proc.getDiagnosticInfo()));

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
            QObject::tr("Failed to remove remote file %1. "
            "Diagnostic info: %2")).arg(desc).arg(proc.getDiagnosticInfo()));

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
            QObject::tr("Failed to remove remote directory %1. "
            "Diagnostic info: %2")).arg(desc).arg(proc.getDiagnosticInfo()));

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
    }
}
