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

#include "OscapScannerBase.h"

#include <QThread>
#include <QAbstractEventDispatcher>
#include <QTemporaryFile>
#include <cassert>

extern "C"
{
#include <xccdf_session.h>
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