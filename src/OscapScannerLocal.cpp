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

#include "OscapScannerLocal.h"
#include "ProcessHelpers.h"
#include "ScanningSession.h"

#include <QThread>
#include <QAbstractEventDispatcher>
#include <QTemporaryFile>

extern "C"
{
#include <xccdf_session.h>
}

OscapScannerLocal::OscapScannerLocal():
    OscapScannerBase()
{}

OscapScannerLocal::~OscapScannerLocal()
{}

void OscapScannerLocal::evaluate()
{
    emit infoMessage("Querying capabilities...");

    {
        SyncProcess proc(this);
        proc.setCommand(SCAP_WORKBENCH_LOCAL_OSCAP_PATH);
        proc.setArguments(QStringList("--v"));
        proc.run();

        if (proc.getExitCode() != 0)
        {
            emit errorMessage(
                QString("Failed to query capabilities of oscap on local machine.\n"
                    "Diagnostic info:\n%1").arg(proc.getDiagnosticInfo())
            );

            mCancelRequested = true;
            signalCompletion(mCancelRequested);
            return;
        }

        mCapabilities.parse(proc.getStdOutContents());
    }

    if (!checkPrerequisites())
    {
        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return;
    }

    // TODO: Error handling!
    emit infoMessage("Creating temporary files...");

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

    emit infoMessage("Starting the oscap process...");
    QProcess process(this);

    QStringList args;

    QTemporaryFile inputARFFile;
    inputARFFile.setAutoRemove(true);

    if (mScannerMode == SM_OFFLINE_REMEDIATION)
    {
        inputARFFile.open();
        inputARFFile.write(getARFForRemediation());
        inputARFFile.close();

        args = buildOfflineRemediationArgs(inputARFFile.fileName(),
                resultFile.fileName(),
                reportFile.fileName(),
                arfFile.fileName());
    }
    else
    {
        const QString inputFile = xccdf_session_get_filename(mSession->getXCCDFSession());

        args = buildEvaluationArgs(inputFile,
                resultFile.fileName(),
                reportFile.fileName(),
                arfFile.fileName(),
                mScannerMode == SM_SCAN_ONLINE_REMEDIATION);
    }

#if SCAP_WORKBENCH_OSCAP_LOCAL_NICENESS != 0
    args.prepend(SCAP_WORKBENCH_LOCAL_OSCAP_PATH);
    args.prepend(QString::number(SCAP_WORKBENCH_OSCAP_LOCAL_NICENESS));
    args.prepend("-n");

    process.start(SCAP_WORKBENCH_LOCAL_NICE_PATH, args);
#else
    process.start(SCAP_WORKBENCH_LOCAL_OSCAP_PATH, args);
#endif


    const unsigned int pollInterval = 100;

    emit infoMessage("Processing...");
    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        while (tryToReadLine(process));
        watchStdErr(process);

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mScanThread)->processEvents(QEventLoop::AllEvents);

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
        bool killed = false;
        while (!process.waitForFinished(pollInterval))
        {
            waited += pollInterval;
            if (waited > 3000) // 3 seconds should be enough for the process to terminate
            {
                emit warningMessage("The oscap process didn't terminate in time, it will be killed instead.");
                // if it didn't terminate, we have to kill it at this point
                process.kill();
                killed = true;
                break;
            }
        }

        if (!killed)
            emit infoMessage("Scanning canceled, the oscap tool has been successfuly terminated.");
    }
    else
    {
        if (process.exitCode() == 1) // error happened
        {
            watchStdErr(process);
            // TODO: pass the diagnostics over
            emit errorMessage("There was an error during evaluation! Exit code of the 'oscap' process was 1.");
            // mark this run as canceled
            mCancelRequested = true;
        }
        else
        {
            // read everything left over
            while (tryToReadLine(process));
            watchStdErr(process);

            emit infoMessage("The oscap tool has finished. Reading results...");

            resultFile.open();
            mResults = resultFile.readAll();
            resultFile.close();

            reportFile.open();
            mReport = reportFile.readAll();
            reportFile.close();

            arfFile.open();
            mARF = arfFile.readAll();
            arfFile.close();

            emit infoMessage("Processing has been finished!");
        }
    }

    signalCompletion(mCancelRequested);
}
