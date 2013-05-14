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

OscapScannerBase::OscapScannerBase():
    Scanner(),

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

void OscapScannerBase::signalCompletion(bool canceled)
{
    Scanner::signalCompletion(canceled);

    // reset the cancel flag now that we have finished XOR canceled
    mCancelRequested = false;
}

QStringList OscapScannerBase::buildEvaluationArgs(const QString& inputFile,
                                                  const QString& resultFile,
                                                  const QString& reportFile,
                                                  const QString& arfFile,
                                                  bool onlineRemediation) const
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

    if (onlineRemediation)
    {
        ret.append("--remediate");
    }

    ret.append(inputFile);

    return ret;
}

QStringList OscapScannerBase::buildOfflineRemediationArgs(const QString& resultInputFile,
                                                          const QString& resultFile,
                                                          const QString& reportFile,
                                                          const QString& arfFile) const
{
    QStringList ret;
    ret.append("xccdf");
    ret.append("remediate");

    ret.append("--results");
    ret.append(resultFile);

    ret.append("--results-arf");
    ret.append(arfFile);

    ret.append("--report");
    ret.append(reportFile);

    ret.append("--progress");

    ret.append(resultInputFile);

    return ret;
}

bool OscapScannerBase::tryToReadLine(QProcess& process)
{
    process.setReadChannel(QProcess::StandardOutput);

    if (!process.canReadLine())
        return false;

    QString stringLine = QString::fromUtf8(process.readLine().constData());
    QStringList split = stringLine.split(":");

    if (split.size() != 2)
    {
        // This is definitely not fatal, it just means that the progress
        // reporting might be off.
        emit warningMessage(QString("Error when parsing scan progress output from stdout of the 'oscap' process. "
                                    "Attempted to split '%1' into 2 fields as rule_id:result and failed. The result "
                                    "doesn't have 2 fields but %2 instead.").arg(stringLine).arg(split.size()));
        // We did read "something".
        return true;
    }

    // NB: trimmed because the line might be padded with either LF or even CR LF
    //     from the right side.
    emit progressReport(split.at(0), split.at(1).trimmed());

    return true;
}

void OscapScannerBase::watchStdErr(QProcess& process)
{
    process.setReadChannel(QProcess::StandardError);

    QString errorMessage = QString::Null();

    while (process.canReadLine())
    {
        // Trailing \n is returned by QProcess::readLine
        errorMessage += process.readLine();
    }

    if (!errorMessage.isEmpty())
    {
        emit warningMessage(QString("The 'oscap' process has written the following content to stderr:\n"
                                    "%1").arg(errorMessage));
    }
}
