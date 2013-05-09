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

void OscapScannerRemoteSsh::setTarget(const QString& target)
{
    OscapScannerBase::setTarget(target);

    if (mSshConnection.isConnected())
        mSshConnection.disconnect();

    mSshConnection.setTarget(target);
}

void OscapScannerRemoteSsh::evaluate()
{
    emit infoMessage("Establishing connecting to remote target...");
    ensureConnected();

    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

    QStringList baseArgs;
    baseArgs.append("-o"); baseArgs.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));
    baseArgs.append(mTarget);

    QString diagnosticInfo;

    emit infoMessage("Querying capabilities of oscap on the remote target...");

    QString mmv;
    if (runProcessSyncStdOut(
            "ssh", baseArgs + QStringList(QString("oscap --v")),
            100, 3000, mmv, diagnosticInfo) != 0)
    {
        emit errorMessage(
            QString("Failed to query capabilities of oscap on remote machine.\n"
                    "Diagnostic info:\n%1").arg(diagnosticInfo)
        );

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return;
    }
    mCapabilities.parse(mmv);

    emit infoMessage("Copying input data to remote target...");
    const QString inputFile = copyInputDataOver();
    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

    const QString reportFile = createRemoteTemporaryFile();
    const QString resultFile = createRemoteTemporaryFile();
    const QString arfFile = createRemoteTemporaryFile();
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
                resultFile,
                reportFile,
                arfFile,
                mScannerMode == SM_SCAN_ONLINE_REMEDIATION);
    }

    const QString sshCmd = args.join(" ");

    emit infoMessage("Starting the remote process...");
    QProcess process(this);
    process.start("ssh", baseArgs + QStringList(QString("oscap %1").arg(sshCmd)));

    const unsigned int pollInterval = 100;

    emit infoMessage("Processing on the remote machine...");
    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        while (tryToReadLine(process));
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
            if (waited > 3000) // 3 seconds should be enough for the process to terminate
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
        while (tryToReadLine(process));
        watchStdErr(process);

        QString tempString;

        diagnosticInfo = "";
        tempString = "";
        if (runProcessSyncStdOut(
            "ssh", baseArgs + QStringList(QString("cat '%1'").arg(resultFile)),
            100, 3000, tempString, diagnosticInfo) != 0)
        {
            emit warningMessage(QString(
                "Failed to copy back XCCDF results. "
                "You will not be able to save them! Diagnostic info: %1").arg(diagnosticInfo));
        }
        mResults = tempString.toUtf8();

        diagnosticInfo = "";
        tempString = "";
        if (runProcessSyncStdOut(
            "ssh", baseArgs + QStringList(QString("cat '%1'").arg(reportFile)),
            100, 3000, tempString, diagnosticInfo) != 0)
        {
            emit warningMessage(QString(
                "Failed to copy back XCCDF report (HTML). "
                "You will not be able to save or view the report! Diagnostic info: %1").arg(diagnosticInfo));
        }
        mReport = tempString.toUtf8();

        diagnosticInfo = "";
        tempString = "";
        if (runProcessSyncStdOut(
            "ssh", baseArgs + QStringList(QString("cat '%1'").arg(arfFile)),
            100, 3000, tempString, diagnosticInfo) != 0)
        {
            emit warningMessage(QString(
                "Failed to copy back Result DataStream (ARF). "
                "You will not be able to save the Result DataStream! Diagnostic info: %1").arg(diagnosticInfo));
        }
        mARF = tempString.toUtf8();
    }

    emit infoMessage("Cleaning up...");

    // Remove all the temporary remote files
    if (runProcessSync(
        "ssh", baseArgs + QStringList(QString("rm '%1'").arg(inputFile)),
        100, 3000, diagnosticInfo) != 0)
    {
        emit warningMessage(QString(
            "Failed to remove remote temporary file with input file content. "
            "Diagnostic info: %1").arg(diagnosticInfo));
    }
    if (runProcessSync(
        "ssh", baseArgs + QStringList(QString("rm '%1'").arg(resultFile)),
        100, 3000, diagnosticInfo) != 0)
    {
        emit warningMessage(QString(
            "Failed to remove remote temporary files with XCCDF result content. "
            "Diagnostic info: %1").arg(diagnosticInfo));
    }
    if (runProcessSync(
        "ssh", baseArgs + QStringList(QString("rm '%1'").arg(reportFile)),
        100, 3000, diagnosticInfo) != 0)
    {
        emit warningMessage(QString(
            "Failed to remove remote temporary files with HTML report content. "
            "Diagnostic info: %1").arg(diagnosticInfo));
    }
    if (runProcessSync(
        "ssh", baseArgs + QStringList(QString("rm '%1'").arg(arfFile)),
        100, 3000, diagnosticInfo) != 0)
    {
        emit warningMessage(QString(
            "Failed to remove remote temporary files with Result DataStream (ARF) content. "
            "Diagnostic info: %1").arg(diagnosticInfo));
    }

    emit infoMessage("Processing has been finished!");
    signalCompletion(mCancelRequested);
}

void OscapScannerRemoteSsh::ensureConnected()
{
    if (!mSshConnection.isConnected())
    {
        try
        {
            mSshConnection.connect();
        }
        catch(const SshConnectionException& e)
        {
            emit errorMessage("Can't connect to remote machine! Exception was: " + QString(e.what()));
            mCancelRequested = true;
        }
    }
}

QString OscapScannerRemoteSsh::copyInputDataOver()
{
    ensureConnected();

    QString ret = createRemoteTemporaryFile();

    QTemporaryFile inputARFFile;
    inputARFFile.setAutoRemove(true);

    QStringList args;
    QString diagnosticInfo;
    args.append("-o"); args.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));
    if (mScannerMode == SM_OFFLINE_REMEDIATION)
    {
        inputARFFile.open();
        inputARFFile.write(getARFForRemediation());
        inputARFFile.close();

        args.append(inputARFFile.fileName());
    }
    else
    {
        args.append(xccdf_session_get_filename(mSession));
    }
    args.append(QString("%1:/%2").arg(mTarget).arg(ret));

    if (runProcessSync("scp", args, 100, 3000, diagnosticInfo) != 0)
    {
        emit errorMessage(
            QString("Failed to copy input data over to the remote machine! "
                    "Diagnostic info:\n%1").arg(diagnosticInfo)
        );

        mCancelRequested = true;
    }

    return ret;
}

QString OscapScannerRemoteSsh::createRemoteTemporaryFile(bool cancelOnFailure)
{
    ensureConnected();

    QStringList args;
    QString diagnosticInfo;

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));
    args.append(mTarget);
    args.append(QString("mktemp"));

    QString ret = "";
    if (runProcessSyncStdOut("ssh", args, 100, 3000, ret, diagnosticInfo) != 0)
    {
        emit errorMessage(
            QString("Failed to create a valid temporary file to copy input "
                    "data to! Diagnostic info: %1").arg(diagnosticInfo)
        );

        mCancelRequested = true;
    }

    return ret.trimmed();
}
