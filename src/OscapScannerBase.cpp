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

bool OscapScannerBase::checkPrerequisites()
{
    if (!mCapabilities.baselineSupport())
    {
        emit errorMessage(
            QString("oscap tool doesn't support basic features required for workbench. "
                "Please make sure you have openscap 0.8.0 or newer. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        mCancelRequested = true;
        return false;
    }

    if (mScannerMode == SM_SCAN_ONLINE_REMEDIATION && !mCapabilities.onlineRemediation())
    {
        emit errorMessage(
            QString("oscap tool doesn't support online remediation. "
                "Please make sure you have openscap 0.9.5 or newer if you want "
                "to use online remediation. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        mCancelRequested = true;
        return false;
    }

    if (mScannerMode == SM_OFFLINE_REMEDIATION && !mCapabilities.ARFInput())
    {
        emit errorMessage(
            QString("oscap tool doesn't support taking ARFs (result datastreams) as input. "
                "Please make sure you have openscap <NOT IMPLEMENTED YET> or newer if you want "
                "to use offline remediation. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        mCancelRequested = true;
        return false;
    }

    if (xccdf_session_is_sds(mSession) && !mCapabilities.sourceDatastreams())
    {
        emit errorMessage(
            QString("oscap tool doesn't support source datastreams as input. "
                "Please make sure you have openscap 0.9.0 or newer if you want "
                "to use source datastreams. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        mCancelRequested = true;
        return false;
    }

    return true;
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

    if (mCapabilities.progressReporting())
        ret.append("--progress");

    if (onlineRemediation && mCapabilities.onlineRemediation())
        ret.append("--remediate");

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

    if (mCapabilities.progressReporting())
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

    if (!mCapabilities.progressReporting())
        return true; // We did read something but it's not in a format we can parse.

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
