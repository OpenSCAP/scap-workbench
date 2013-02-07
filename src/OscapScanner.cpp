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
        ret.append("--component_id");
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

    QString inputFile = xccdf_session_get_filename(mSession);

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
{
    mMasterSocket.setAutoRemove(false);
}

OscapScannerRemoteSsh::~OscapScannerRemoteSsh()
{
    if (mMasterSocket.fileName() != QString::Null())
    {
        QProcess socketClosing;

        QStringList args;
        args.append("-S"); args.append(mMasterSocket.fileName());

        args.append("-O"); args.append("exit");
        args.append(mTarget);

        socketClosing.start("ssh", args);
        socketClosing.waitForFinished(1000);
    }
}

void OscapScannerRemoteSsh::evaluate()
{
    establish();

    if (mCancelRequested)
        signalCompletion(true);
}

void OscapScannerRemoteSsh::establish()
{
    // These two calls force Qt to allocate the file on disk and give us
    // the path back.
    mMasterSocket.open();
    mMasterSocket.close();

    QStringList args;
    args.append("-M");
    args.append("-f");
    args.append("-N");

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket.fileName()));

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

    // TODO: Check this differently
    //assert(mMasterProcess->exitCode() == 0);
}
