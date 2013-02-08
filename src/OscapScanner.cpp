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

#include "OscapScanner.h"

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

OscapScannerBase::OscapScannerBase(QThread* thread, struct xccdf_session* session, const QString& target):
    Scanner(thread, session, target),

    mCancelRequested(false)
{}

OscapScannerBase::~OscapScannerBase()
{}

void OscapScannerBase::cancel()
{
    // NB: No need for mutexes here, this will be run in the same thread because
    //     the event queue we pump in evaluate will run it.
    mCancelRequested = true;
}

void OscapScannerBase::getResults(QByteArray& destination)
{
    assert(!mCancelRequested);

    destination.append(mResults);
}

void OscapScannerBase::getReport(QByteArray& destination)
{
    assert(!mCancelRequested);

    destination.append(mReport);
}

void OscapScannerBase::getARF(QByteArray& destination)
{
    assert(!mCancelRequested);

    destination.append(mARF);
}

int OscapScannerBase::runProcessSync(const QString& cmd, const QStringList& args,
                                     unsigned int pollInterval,
                                     unsigned int termLimit,
                                     QString& diagnosticInfo)
{
    QProcess process(this);
    process.start(cmd, args);

    diagnosticInfo += QString("Starting process '") + cmd + QString(" ") + args.join(" ") + QString("'\n");

    while (!process.waitForFinished(pollInterval))
    {
        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            diagnosticInfo += "Cancel was requested! Sending terminate signal to the process...\n";

            // TODO: On Windows we have to kill immediately, terminate() posts WM_CLOSE
            //       but oscap doesn't have any event loop running.
            process.terminate();
            break;
        }
    }

    if (mCancelRequested)
    {
        unsigned int termWaited = 0;

        while (!process.waitForFinished(pollInterval))
        {
            QAbstractEventDispatcher::instance(mThread)->processEvents(QEventLoop::AllEvents);
            termWaited += pollInterval;

            if (termWaited > termLimit)
            {
                diagnosticInfo += QString("Process had to be killed! Didn't terminate after %1 msec of waiting.\n").arg(termWaited);
                process.kill();
                break;
            }
        }
    }

    diagnosticInfo += "stdout:\n===============================\n" + QString(process.readAllStandardOutput()) + QString("\n");
    diagnosticInfo += "stderr:\n===============================\n" + QString(process.readAllStandardError()) + QString("\n");

    return process.exitCode();
}

QStringList OscapScannerBase::buildCommandLineArgs(const QString& inputFile,
                                                   const QString& resultFile,
                                                   const QString& reportFile,
                                                   const QString& arfFile)
{
    QStringList ret;
    ret.append("xccdf");
    ret.append("eval");

    const char* datastream_id = xccdf_session_get_datastream_id(mSession);
    const char* component_id = xccdf_session_get_component_id(mSession);

    if (datastream_id)
    {
        ret.append("--datastream-id");
        ret.append(datastream_id);
    }

    if (component_id)
    {
        ret.append("--xccdf-id");
        ret.append(component_id);
    }

    const char* profile_id = xccdf_session_get_profile_id(mSession);

    if (profile_id)
    {
        ret.append("--profile");
        ret.append(profile_id);
    }

    ret.append("--results");
    ret.append(resultFile);

    ret.append("--results-arf");
    ret.append(arfFile);

    ret.append("--report");
    ret.append(reportFile);

    ret.append("--progress");

    ret.append(inputFile);

    return ret;
}

bool OscapScannerBase::tryToReadLine(QProcess& process)
{
    if (!process.canReadLine())
        return false;

    QString stringLine = QString::fromUtf8(process.readLine().constData());
    QStringList split = stringLine.split(":");

    // TODO: error handling!

    // NB: trimmed because the line might be padded with either LF or even CR LF
    //     from the right side.
    emit progressReport(split.at(0), split.at(1).trimmed());

    return true;
}

OscapScannerLocal::OscapScannerLocal(QThread* thread, struct xccdf_session* session, const QString& target):
    OscapScannerBase(thread, session, target)
{}

OscapScannerLocal::~OscapScannerLocal()
{}

void OscapScannerLocal::evaluate()
{
    // TODO: Error handling!

    QTemporaryFile resultFile;
    resultFile.setAutoRemove(true);
    // the following forces Qt to give us the filename
    resultFile.open(); resultFile.close();

    QTemporaryFile reportFile;
    reportFile.setAutoRemove(true);
    reportFile.open(); reportFile.close();

    QTemporaryFile arfFile;
    arfFile.setAutoRemove(true);
    arfFile.open(); arfFile.close();

    const QString inputFile = xccdf_session_get_filename(mSession);

    QProcess process(this);
    process.start("oscap", buildCommandLineArgs(inputFile,
                                                resultFile.fileName(),
                                                reportFile.fileName(),
                                                arfFile.fileName()));

    const unsigned int pollInterval = 100;

    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        while (tryToReadLine(process));

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
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

        resultFile.open();
        mResults = resultFile.readAll();
        resultFile.close();

        reportFile.open();
        mReport = reportFile.readAll();
        reportFile.close();

        arfFile.open();
        mARF = arfFile.readAll();
        arfFile.close();
    }

    signalCompletion(mCancelRequested);
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
    establish();
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
