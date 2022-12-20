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

#include <stdexcept>
#include <QThread>
#include <QAbstractEventDispatcher>

extern "C"
{
#include <xccdf_session.h>
}

void OscapScannerLocal::setFilenameToTempFile(SpacelessQTemporaryFile& file)
{
    file.open();
    file.close();
}


void OscapScannerLocal::fillInCapabilities()
{
    SyncProcess proc(this);
    proc.setCommand(SCAP_WORKBENCH_LOCAL_OSCAP_PATH);
    proc.setArguments(QStringList("-V"));
    proc.run();

    if (proc.getExitCode() != 0)
    {
        QString message = QObject::tr("Failed to query capabilities of oscap on local machine.\n"
                "Diagnostic info:\n%1").arg(proc.getDiagnosticInfo());

        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        throw std::runtime_error(message.toUtf8().constData());
    }

    mCapabilities.parse(proc.getStdOutContents());
}

void OscapScannerLocal::evaluate()
{
    if (mDryRun)
    {
        signalCompletion(mCancelRequested);
        return;
    }

    emit infoMessage(QObject::tr("Querying capabilities..."));
    try
    {
        fillInCapabilities();
    }
    catch (std::exception& e)
    {
        emit errorMessage(e.what());
        return;
    }

    if (!checkPrerequisites())
    {
        mCancelRequested = true;
        signalCompletion(mCancelRequested);
        return;
    }

    // TODO: Error handling!
    // This is mainly for check-engine-results and oval-results, to ensure
    // we get a full report, including info from these files. openscap's XSLT
    // uses info in the check engine results if it can find them.

    QProcess process(this);

    emit infoMessage(QObject::tr("Creating temporary files..."));
    // This is mainly for check-engine-results and oval-results, to ensure
    // we get a full report, including info from these files. openscap's XSLT
    // uses info in the check engine results if it can find them.
    SpacelessQTemporaryDir workingDir;
    process.setWorkingDirectory(workingDir.path());

    QStringList args;
    SpacelessQTemporaryFile inputARFFile;

    SpacelessQTemporaryFile arfFile;
    arfFile.setAutoRemove(true);
    setFilenameToTempFile(arfFile);

    SpacelessQTemporaryFile reportFile;
    reportFile.setAutoRemove(true);
    setFilenameToTempFile(reportFile);

    SpacelessQTemporaryFile resultFile;
    resultFile.setAutoRemove(true);
    setFilenameToTempFile(resultFile);


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
        args = buildEvaluationArgs(mSession->getOpenedFilePath(),
                mSession->hasTailoring() ? mSession->getTailoringFilePath() : QString(),
                resultFile.fileName(),
                reportFile.fileName(),
                arfFile.fileName(),
                mScannerMode == SM_SCAN_ONLINE_REMEDIATION);
    }
    QString program = getOscapProgramAndAdaptArgs(args);

    emit infoMessage(QObject::tr("Starting the oscap process..."));
    process.start(program, args);
    process.waitForStarted();

    if (process.state() != QProcess::Running)
    {
        emit errorMessage(QObject::tr("Failed to start local scanning process '%1'. Perhaps the executable was not found?").arg(program));
        mCancelRequested = true;
    }

    unsigned int pollInterval = 100;

    emit infoMessage(QObject::tr("Processing..."));
    while (!process.waitForFinished(pollInterval))
    {
        // read everything new
        readStdOut(process);
        watchStdErr(process);

        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(mScanThread)->processEvents(QEventLoop::AllEvents);

        if (mCancelRequested)
        {
            pollInterval = 1000;
            emit infoMessage(QObject::tr("Cancellation was requested! Terminating scanning..."));
            process.kill();
        }
    }

    if (!mCancelRequested)
    {
        if (process.exitCode() == 1) // error happened
        {
            watchStdErr(process);
            // TODO: pass the diagnostics over
            emit errorMessage(QObject::tr("There was an error during evaluation! Exit code of the 'oscap' process was 1."));
            // mark this run as canceled
            mCancelRequested = true;
        }
        else
        {
            // read everything left over
            readStdOut(process);
            watchStdErr(process);

            emit infoMessage(QObject::tr("The oscap tool has finished. Reading results..."));

            resultFile.open();
            mResults = resultFile.readAll();
            resultFile.close();

            reportFile.open();
            mReport = reportFile.readAll();
            reportFile.close();

            arfFile.open();
            mARF = arfFile.readAll();
            arfFile.close();

            emit infoMessage(QObject::tr("Processing has been finished!"));
        }
    }
    else
    {
        emit infoMessage(QObject::tr("Scanning cancelled!"));
    }

    signalCompletion(mCancelRequested);
}

OscapScannerLocal::OscapScannerLocal():
    OscapScannerBase()
{}

OscapScannerLocal::~OscapScannerLocal()
{}

QStringList OscapScannerLocal::getCommandLineArgs() const
{
    // TODO: This seems outdated (and it is used only during dry runs)
    QStringList args("oscap");

    if (mScannerMode == SM_OFFLINE_REMEDIATION)
    {
        SpacelessQTemporaryFile inputARFFile;
        inputARFFile.setAutoRemove(true);
        inputARFFile.open();
        inputARFFile.write(getARFForRemediation());
        inputARFFile.close();

        args += buildOfflineRemediationArgs(inputARFFile.fileName(),
            "/tmp/xccdf-results.xml",
            "/tmp/report.html",
            "/tmp/arf.xml",
            // ignore capabilities because of dry-run
            true
        );
    }
    else
    {
        args += buildEvaluationArgs(mSession->getOpenedFilePath(),
            mSession->getUserTailoringFilePath(),
            "/tmp/xccdf-results.xml",
            "/tmp/report.html",
            "/tmp/arf.xml",
            mScannerMode == SM_SCAN_ONLINE_REMEDIATION,
            // ignore capabilities because of dry-run
            true
        );
    }

    args.removeOne("--progress");

    return args;
}

QString OscapScannerLocal::getPkexecOscapPath()
{
    const QByteArray path = qgetenv("SCAP_WORKBENCH_PKEXEC_OSCAP_PATH");

    if (path.isEmpty())
        return SCAP_WORKBENCH_LOCAL_PKEXEC_OSCAP_PATH;
    else
        return path;
}

QString OscapScannerLocal::getOscapProgramAndAdaptArgs(QStringList& args)
{
    QString program;
#ifdef SCAP_WORKBENCH_LOCAL_NICE_FOUND
    args.prepend(getPkexecOscapPath());
    args.prepend(QString::number(SCAP_WORKBENCH_LOCAL_OSCAP_NICENESS));
    args.prepend("-n");

    program = SCAP_WORKBENCH_LOCAL_NICE_PATH;
#else
    program = getPkexecOscapPath();
#endif
    return program;
}
