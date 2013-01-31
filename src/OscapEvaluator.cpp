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

#include "OscapEvaluator.h"

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

OscapEvaluatorBase::OscapEvaluatorBase(QThread* thread, struct xccdf_session* session, const QString& target):
    Evaluator(thread, session, target)
{}

OscapEvaluatorBase::~OscapEvaluatorBase()
{}

QStringList OscapEvaluatorBase::buildCommandLineArgs(const QString& inputFile, const QString& resultFile)
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

    ret.append("--progress");

    ret.append(inputFile);

    return ret;
}

OscapEvaluatorLocal::OscapEvaluatorLocal(QThread* thread, struct xccdf_session* session, const QString& target):
    OscapEvaluatorBase(thread, session, target),

    mCancelRequested(false)
{}

OscapEvaluatorLocal::~OscapEvaluatorLocal()
{}

void OscapEvaluatorLocal::evaluate()
{
    // TODO: Error handling!
    QTemporaryFile resultFile;
    resultFile.setAutoRemove(true);
    // the following 2 lines force Qt to give us the filename
    resultFile.open();
    resultFile.close();

    QString inputFile = xccdf_session_get_filename(mSession);

    QProcess process(this);
    process.start("oscap", buildCommandLineArgs(inputFile, resultFile.fileName()));

    const unsigned int pollInterval = 100;

    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        while (tryToReadLine(process));

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance()->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            process.close();
            break;
        }
    }

    if (!mCancelRequested)
    {
        // read everything left over
        while (tryToReadLine(process));

        resultFile.open();
        mResults = resultFile.readAll();
        resultFile.close();
    }

    signalCompletion(mCancelRequested);
}

void OscapEvaluatorLocal::cancel()
{
    // NB: No need for mutexes here, this will be run in the same thread because
    //     the event queue we pump in evaluate will run it.
    mCancelRequested = true;
}

QByteArray OscapEvaluatorLocal::getResults()
{
    assert(!mCancelRequested);

    return mResults;
}

bool OscapEvaluatorLocal::tryToReadLine(QProcess& process)
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
