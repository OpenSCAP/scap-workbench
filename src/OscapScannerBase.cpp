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
#include "ScanningSession.h"

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

    mLastRuleID(""),
    mLastDownloadingFile(""),
    mReadingState(RS_READING_PREFIX),
    mReadBuffer(""),
    mCancelRequested(false)
{
    mReadBuffer.reserve(256);
}

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

    mLastRuleID = "";
    mLastDownloadingFile = "";
    mReadingState = RS_READING_PREFIX;
    mReadBuffer = "";

    // reset the cancel flag now that we have finished XOR canceled
    mCancelRequested = false;
}

bool OscapScannerBase::checkPrerequisites()
{
    if (!mCapabilities.baselineSupport())
    {
        emit errorMessage(
            QObject::tr("oscap tool doesn't support basic features required for workbench. "
                "Please make sure you have openscap 0.8.0 or newer. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        return false;
    }

    if (mScannerMode == SM_SCAN_ONLINE_REMEDIATION && !mCapabilities.onlineRemediation())
    {
        emit errorMessage(
            QObject::tr("oscap tool doesn't support online remediation. "
                "Please make sure you have openscap 0.9.5 or newer if you want "
                "to use online remediation. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        return false;
    }

    if (mScannerMode == SM_OFFLINE_REMEDIATION && !mCapabilities.ARFInput())
    {
        emit errorMessage(
            QObject::tr("oscap tool doesn't support taking ARFs (result datastreams) as input. "
                "Please make sure you have openscap <NOT IMPLEMENTED YET> or newer if you want "
                "to use offline remediation. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        return false;
    }

    if (mSession->isSDS() && !mCapabilities.sourceDatastreams())
    {
        emit errorMessage(
            QObject::tr("oscap tool doesn't support source datastreams as input. "
                "Please make sure you have openscap 0.9.0 or newer if you want "
                "to use source datastreams. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        return false;
    }

    if (mSession->hasTailoring() && !mCapabilities.tailoringSupport())
    {
        emit errorMessage(
            QObject::tr("oscap tool doesn't support XCCDF tailoring but the session uses tailoring. "
                "Please make sure you have openscap 0.9.12 or newer on the target machine if you "
                "want to use tailoring features of SCAP Workbench. "
                "oscap version was detected as '%1'.").arg(mCapabilities.getOpenSCAPVersion())
        );

        return false;
    }

    return true;
}

QString OscapScannerBase::surroundQuote(const QString& input) const
{
    if (input.contains(" "))
        return QString("\""+input+"\"");

    return input;
}

QStringList OscapScannerBase::buildEvaluationArgs(const QString& inputFile,
        const QString& tailoringFile,
        const QString& resultFile,
        const QString& reportFile,
        const QString& arfFile,
        bool onlineRemediation,
        bool ignoreCapabilities) const
{
    QStringList ret;
    ret.append("xccdf");
    ret.append("eval");

    if (mSkipValid)
    {
        ret.append("--skip-valid");
    }

    if (mFetchRemoteResources)
    {
        ret.append("--fetch-remote-resources");
    }

    if (mSession->isSDS())
    {
        const QString datastreamId = mSession->getDatastreamID();
        const QString componentId = mSession->getComponentID();

        if (!datastreamId.isEmpty())
        {
            ret.append("--datastream-id");
            ret.append(datastreamId);
        }

        if (!componentId.isEmpty())
        {
            ret.append("--xccdf-id");
            ret.append(componentId);
        }
    }

    if (!tailoringFile.isEmpty())
    {
        ret.append("--tailoring-file");
        if (mDryRun)
            ret.append(surroundQuote(tailoringFile));
        else
            ret.append(tailoringFile);
    }

    const QString profileId = mSession->getProfile();

    if (!profileId.isEmpty())
    {
        ret.append("--profile");
        ret.append(profileId);
    }

    // We don't use these results directly but openscap uses them when generating
    // the HTML report! We get more info in the HTML report if we request OVAL
    // results!
    ret.append("--oval-results");

    ret.append("--results");
    if (mDryRun)
        ret.append(surroundQuote(resultFile));
    else
        ret.append(resultFile);

    ret.append("--results-arf");
    if (mDryRun)
        ret.append(surroundQuote(arfFile));
    else
        ret.append(arfFile);

    ret.append("--report");
    if (mDryRun)
        ret.append(surroundQuote(reportFile));
    else
        ret.append(reportFile);

    if (ignoreCapabilities || mCapabilities.progressReporting())
        ret.append("--progress");

    if (onlineRemediation && (ignoreCapabilities || mCapabilities.onlineRemediation()))
        ret.append("--remediate");

    if (mDryRun)
        ret.append(surroundQuote(inputFile));
    else
        ret.append(inputFile);

    return ret;
}

QStringList OscapScannerBase::buildOfflineRemediationArgs(const QString& resultInputFile,
        const QString& resultFile,
        const QString& reportFile,
        const QString& arfFile,
        bool ignoreCapabilities) const
{
    QStringList ret;
    ret.append("xccdf");
    ret.append("remediate");

    if (mSkipValid)
    {
        ret.append("--skip-valid");
    }

    // We don't use these results directly but openscap uses them when generating
    // the HTML report! We get more info in the HTML report if we request OVAL
    // results!
    ret.append("--oval-results");

    ret.append("--results");
    ret.append(resultFile);

    ret.append("--results-arf");
    ret.append(arfFile);

    ret.append("--report");
    ret.append(reportFile);

    if (ignoreCapabilities || mCapabilities.progressReporting())
        ret.append("--progress");

    ret.append(resultInputFile);

    return ret;
}

bool OscapScannerBase::tryToReadStdOutChar(QProcess& process)
{
    char readChar = '\0';
    if (!process.getChar(&readChar))
        return false;

    if (!mCapabilities.progressReporting())
        return true; // We did read something but it's not in a format we can parse.

    if (readChar == ':')
    {
        switch (mReadingState)
        {
            case RS_READING_PREFIX:
                {
                    // Openscap <= 1.2.10 (60fb9f0c98eee) sends this message through stdout
                    if (mReadBuffer=="Downloading")
                    {
                         mReadingState = RS_READING_DOWNLOAD_FILE;
                    }
                    else
                    {
                        mLastRuleID = mReadBuffer;
                        emit progressReport(mLastRuleID, "processing");
                        mReadingState = RS_READING_RULE_RESULT;
                    }
                    mReadBuffer = "";
                }
                break;

            case RS_READING_RULE_RESULT:
                {
                    emit warningMessage(QString(
                                QObject::tr("Error when parsing scan progress output from stdout of the 'oscap' process. "
                                    "':' encountered while not reading rule ID, newline and/or rule result are missing! "
                                    "Read buffer is '%1'.")).arg(mReadBuffer));
                    mReadBuffer = "";
                }
                break;
            case RS_READING_DOWNLOAD_FILE:
                {
                    // When fetching remote content, openscap will inform scap-workbench about
                    // resources being downloaded. Keep any colon found in URL of file being downloaded.
                    mReadBuffer.append(QChar::fromAscii(readChar));
                }
                break;

            default:
                // noop
                break;
        }
    }
    else if (readChar == '\n')
    {
        switch(mReadingState)
        {
            case RS_READING_PREFIX:
                // If we found a '\n' while reading prefix, we might have received an error or
                // warning message through stdout.
                if (mReadBuffer.contains("--fetch-remote-resources"))
                {
                    // If message is about --fetch-remote-resources, emit a nice warning.
                    // This is needed for workbench to be able to handle messages from machines
                    // running older versions of openscap.
                    // From openscap version 1.2.11, this message is sent through stderr
                    // and therefore is handled accordingly by workbench.
                    emit warningMessage(guiFriendlyMessage(mReadBuffer));
                }
                else
                {
                    // No other error or warning messages are expected through stdout,
                    // so it is likely that a parsing error occured.
                    emit warningMessage(QString(
                                QObject::tr("Error when parsing scan progress output from stdout of the 'oscap' process. "
                                    "Newline encountered while reading rule ID, rule result and/or ':' are missing! "
                                    "Read buffer is '%1'.")).arg(mReadBuffer));
                }
                break;

            case RS_READING_RULE_RESULT:
                emit progressReport(mLastRuleID, mReadBuffer);
                break;

            case RS_READING_DOWNLOAD_FILE_STATUS:
                {
                    QString downloadStatus = mReadBuffer.mid(1);
                    if (downloadStatus == "ok")
                        emit infoMessage(QString("Downloading of \"%1\" finished: %2").arg(mLastDownloadingFile).arg(downloadStatus));
                    else
                        emit warningMessage(QString("Failed to download \"%1\"!").arg(mLastDownloadingFile));
                }
                break;
        }
        mReadingState = RS_READING_PREFIX;
        mReadBuffer = "";
    }
    else if ( (readChar == '.') && (mReadingState == RS_READING_DOWNLOAD_FILE) && (mReadBuffer.endsWith(" ..")))
    {
        int urlLen = mReadBuffer.length();
        urlLen -= 1; // without first space
        urlLen -= 3; // without "progress dots"
        mLastDownloadingFile = mReadBuffer.mid(1, urlLen);

        emit infoMessage(QString("Downloading of \"%1\"...").arg(mLastDownloadingFile));

        mReadBuffer = "";
        mReadingState = RS_READING_DOWNLOAD_FILE_STATUS;
    }
    else
    {
        // we know for sure that buffer[0] can only contain ASCII characters
        // (IDs and special keywords regarding rule status)
        mReadBuffer.append(QChar::fromAscii(readChar));
    }

    return true;
}

void OscapScannerBase::readStdOut(QProcess& process)
{
    process.setReadChannel(QProcess::StandardOutput);

    while (tryToReadStdOutChar(process));
}

void OscapScannerBase::watchStdErr(QProcess& process)
{
    process.setReadChannel(QProcess::StandardError);

    QString stdErrOutput("");

    // As readStdOut() is greedy and will continue reading for as long as there is output for it,
    // by the time we come to handle sdterr output there may be multiple warning and/or error messages.
    while (process.canReadLine())
    {
        // Trailing \n is returned by QProcess::readLine
        stdErrOutput = process.readLine();

        if (!stdErrOutput.isEmpty())
        {
            if (stdErrOutput.contains("WARNING: "))
            {
                QString guiMessage = guiFriendlyMessage(stdErrOutput);
                emit warningMessage(QObject::tr(guiMessage.toUtf8().constData()));
            }
            // Openscap >= 1.2.11 (60fb9f0c98eee) sends this message through stderr
            else if (stdErrOutput.contains(QRegExp("^Downloading: .+ \\.{3} \\w+\\n")))
            {
                emit infoMessage(stdErrOutput);
            }
            else
            {
                emit errorMessage(QObject::tr("The 'oscap' process has written the following content to stderr:\n"
                                            "%1").arg(stdErrOutput));
            }
        }

    }

}

QString OscapScannerBase::guiFriendlyMessage(const QString& cliMessage)
{
    QString guiMessage = cliMessage;

    // Remove "WARNING:" prefix and trailing \n
    guiMessage.remove(QRegExp("(WARNING: )|\n"));

    if (cliMessage.contains("--fetch-remote-resources"))
        guiMessage = QString("Remote resources might be necessary for this profile to work properly. Please select \"Fetch remote resources\" for complete scan");
    return guiMessage;
}
