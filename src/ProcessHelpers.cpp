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

#include "ProcessHelpers.h"
#include "Exceptions.h"

#include <QProcess>
#include <QEventLoop>
#include <QAbstractEventDispatcher>

SyncProcess::SyncProcess(QObject* parent):
    QObject(parent),

    mPollInterval(100),
    mTermLimit(3000),

    mRunning(false),
    mCancelRequestSource(0),
    mLocalCancelRequested(false),

    mExitCode(-1)
{}

SyncProcess::~SyncProcess()
{}

void SyncProcess::setCommand(const QString& command)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change command!");

    mCommand = command;
}

void SyncProcess::setArguments(const QStringList& args)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change arguments!");

    mArguments = args;
}

void SyncProcess::setCancelRequestSource(bool* source)
{
    mCancelRequestSource = source;
}

void SyncProcess::run()
{
    mDiagnosticInfo = "";

    QProcess process(this);
    mDiagnosticInfo += QString("Starting process '") + generateDescription() + QString("'\n");
    process.start(generateFullCommand(), generateFullArguments());

    mRunning = true;

    while (!process.waitForFinished(mPollInterval))
    {
        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(thread())->processEvents(QEventLoop::AllEvents);

        if (wasCancelRequested())
        {
            mDiagnosticInfo += "Cancel was requested! Sending terminate signal to the process...\n";

            // TODO: On Windows we have to kill immediately, terminate() posts WM_CLOSE
            //       but oscap doesn't have any event loop running.
            process.terminate();
            break;
        }
    }

    if (wasCancelRequested())
    {
        unsigned int termWaited = 0;

        while (!process.waitForFinished(mPollInterval))
        {
            QAbstractEventDispatcher::instance(thread())->processEvents(QEventLoop::AllEvents);
            termWaited += mPollInterval;

            if (termWaited > mTermLimit)
            {
                mDiagnosticInfo += QString("Process had to be killed! Didn't terminate after %1 msec of waiting.\n").arg(termWaited);
                process.kill();
                break;
            }
        }
    }

    mRunning = false;

    mStdOutContents = process.readAllStandardOutput();
    mStdErrContents = process.readAllStandardError();

    // TODO: We are duplicating data here!
    mDiagnosticInfo += "stdout:\n===============================\n" + QString(mStdOutContents) + QString("\n");
    mDiagnosticInfo += "stderr:\n===============================\n" + QString(mStdErrContents) + QString("\n");

    mExitCode = process.exitCode();
}

void SyncProcess::cancel()
{
    mLocalCancelRequested = true;
}

bool SyncProcess::isRunning() const
{
    return mRunning;
}

int SyncProcess::getExitCode() const
{
    if (isRunning())
        throw SyncProcessException("Can't query exit code when the process is running!");

    return mExitCode;
}

const QString& SyncProcess::getStdOutContents() const
{
    if (isRunning())
        throw SyncProcessException("Can't query stdout when the process is running!");

    return mStdOutContents;
}

const QString& SyncProcess::getStdErrContents() const
{
    if (isRunning())
        throw SyncProcessException("Can't query stderr when the process is running!");

    return mStdErrContents;
}

const QString& SyncProcess::getDiagnosticInfo() const
{
    if (isRunning())
        throw SyncProcessException("Can't query diagnostic info when the process is running!");

    return mDiagnosticInfo;
}

bool SyncProcess::wasCancelRequested() const
{
    return mLocalCancelRequested || (mCancelRequestSource && *mCancelRequestSource);
}

QString SyncProcess::generateFullCommand() const
{
    return mCommand;
}

QStringList SyncProcess::generateFullArguments() const
{
    return mArguments;
}

QString SyncProcess::generateDescription() const
{
    return mCommand + QString(" ") + mArguments.join(" ");
}
