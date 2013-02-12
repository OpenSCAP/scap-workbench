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
#include <iostream>
#include <cassert>

extern "C"
{
#include <xccdf_session.h>
#include <xccdf_benchmark.h>
}

OscapScannerRemoteSsh::OscapScannerRemoteSsh(QThread* thread, struct xccdf_session* session, const QString& target):
    OscapScannerBase(thread, session, target)
{}

OscapScannerRemoteSsh::~OscapScannerRemoteSsh()
{
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
    }
}

void OscapScannerRemoteSsh::evaluate()
{
    emit infoMessage("Establishing connecting to remote target...");
    establish();
    emit infoMessage("Copying input data to remote target...");
    copyInputDataOver();

    if (mCancelRequested)
        signalCompletion(true);

    const QString inputFile = xccdf_session_get_filename(mSession);
    const QString reportFile = "/tmp/test.oscap.report";
    const QString resultFile = "/tmp/test.oscap.result";
    const QString arfFile = "/tmp/test.oscap.arf";

    const QString sshCmd =  buildCommandLineArgs(inputFile,
                                                 resultFile,
                                                 reportFile,
                                                 arfFile).join(" ");

    QStringList args;
    args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));
    args.append(mTarget);
    args.append(QString("\"oscap %1\"").arg(sshCmd));

    std::cout << "oscap " << sshCmd.toUtf8().constData() << std::endl;

    emit infoMessage("Starting the remote scanning process...");
    QProcess process(this);
    process.start("ssh", args);

    const unsigned int pollInterval = 100;

    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        while (tryToReadLine(process));

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

/*        resultFile.open();
        mResults = resultFile.readAll();
        resultFile.close();

        reportFile.open();
        mReport = reportFile.readAll();
        reportFile.close();

        arfFile.open();
        mARF = arfFile.readAll();
        arfFile.close();*/
    }

    signalCompletion(mCancelRequested);
}

void OscapScannerRemoteSsh::establish()
{
    mMasterSocket = "/tmp/oscap.socket";

    std::cout << mMasterSocket.toUtf8().constData() << std::endl;

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

    std::cout << "Master socket created" << std::endl;

    // TODO: Check this differently
    assert(mMasterProcess->exitCode() == 0);
}

QString OscapScannerRemoteSsh::copyInputDataOver()
{
    QString ret = "/tmp/test.oscap.remote";

    QStringList args;
    args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));
    args.append(xccdf_session_get_filename(mSession));
    args.append(QString("%1:/%2").arg(mTarget).arg(ret));

    QString diagnosticInfo;
    if (runProcessSync("scp", args, 100, 3000, diagnosticInfo) != 0)
    {
        // TODO: handle errors
    }

    std::cout << "Input data copied" << std::endl;

    return ret;
}