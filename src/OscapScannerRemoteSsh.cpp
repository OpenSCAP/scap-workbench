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

#include <QThread>
#include <QAbstractEventDispatcher>
#include <QTemporaryFile>
#include <QFileInfo>
#include <QDir>
#include <iostream>
#include <cassert>

extern "C"
{
#include <xccdf_session.h>
#include <xccdf_benchmark.h>
}

OscapScannerRemoteSsh::OscapScannerRemoteSsh(QThread* thread):
    OscapScannerBase(thread)
{}

OscapScannerRemoteSsh::~OscapScannerRemoteSsh()
{
    cleanupMasterSocket();
}

void OscapScannerRemoteSsh::setTarget(const QString& target)
{
    OscapScannerBase::setTarget(target);

    cleanupMasterSocket();
}

void OscapScannerRemoteSsh::evaluate()
{
    emit infoMessage("Establishing connecting to remote target...");
    establish();
    if (mCancelRequested)
    {
        signalCompletion(true);
        return;
    }

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

    const QString sshCmd = buildEvaluationArgs(inputFile,
                                               resultFile,
                                               reportFile,
                                               arfFile,
                                               mScannerMode == SM_SCAN_ONLINE_REMEDIATION).join(" ");

    QStringList baseArgs;
    baseArgs.append("-o"); baseArgs.append(QString("ControlPath=%1").arg(mMasterSocket));
    baseArgs.append(mTarget);

    QString diagnosticInfo;

    emit infoMessage("Starting the remote scanning process...");
    QProcess process(this);
    process.start("ssh", baseArgs + QStringList(QString("oscap %1").arg(sshCmd)));

    const unsigned int pollInterval = 100;

    emit infoMessage("Scanning remotely...");
    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        while (tryToReadLine(process));
        watchStdErr(process);

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            emit infoMessage("Cancelation was requested! Terminating scanning...");
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

    emit infoMessage("Scanning has been finished!");
    signalCompletion(mCancelRequested);
}

void OscapScannerRemoteSsh::establish()
{
    if (mMasterSocket != "")
        // connection already established!
        return;

    QString diagnosticInfo = "";
    if (runProcessSyncStdOut("mktemp", QStringList("-d"), 100, 3000, mMasterSocket, diagnosticInfo) != 0)
    {
        emit errorMessage(
            QString("Failed to create a temporary directory on local machine! Diagnostic info: %1").arg(diagnosticInfo));

        mCancelRequested = true;
        return;
    }

    mMasterSocket = mMasterSocket.trimmed() + "/ssh_socket";

    QStringList args;
    args.append("-M");
    args.append("-f");
    args.append("-N");

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));

    // TODO: sanitize input?
    args.append(mTarget);

    mMasterProcess = new QProcess(this);
    mMasterProcess->start("ssh", args);
    //mMasterProcess->closeWriteChannel();

    while (!mMasterProcess->waitForFinished(100))
    {
        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            mMasterProcess->close();
            break;
        }
    }

    if (mMasterProcess->exitCode() != 0)
    {
        // TODO: Fix unicode woes
        const QString stdout = mMasterProcess->readAllStandardOutput();
        const QString stderr = mMasterProcess->readAllStandardError();

        emit errorMessage(
            QString("Failed to establish connection and create the master ssh socket.\n"
                    "stdout:\n%1\n\n"
                    "stderr:\n%2").arg(stdout).arg(stderr)
        );

        mCancelRequested = true;
    }
}

QString OscapScannerRemoteSsh::copyInputDataOver()
{
    QString ret = createRemoteTemporaryFile();

    QStringList args;
    QString diagnosticInfo;
    args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));
    args.append(xccdf_session_get_filename(mSession));
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
    QStringList args;
    QString diagnosticInfo;

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));
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

void OscapScannerRemoteSsh::cleanupMasterSocket()
{
    // This is just cleanup, don't show any dialogs if we fail at this stage.
    if (mMasterSocket != QString::Null())
    {
        QProcess socketClosing;

        QStringList args;
        args.append("-S"); args.append(mMasterSocket);

        args.append("-O"); args.append("exit");
        args.append(mTarget);

        socketClosing.start("ssh", args);
        if (!socketClosing.waitForFinished(1000))
        {
            socketClosing.kill();
        }

        // delete the parent temporary directory we created
        QFileInfo socketFile(mMasterSocket);
        QDir socketDir = socketFile.dir();

        if (!socketDir.rmdir(socketDir.absolutePath()))
        {
            emit warningMessage(
                QString("Failed to remove temporary directory hosting the ssh "
                        "connection socket."));
        }
    }
}
