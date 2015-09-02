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

#include "ui_ProcessProgress.h"

#include <QProcess>
#include <QEventLoop>
#include <QAbstractEventDispatcher>
#include <cassert>

class ProcessProgressDialog : public QDialog
{
    public:
        ProcessProgressDialog(QWidget* parent = 0):
            QDialog(parent)
        {
            mUI.setupUi(this);
        }

        virtual ~ProcessProgressDialog()
        {}

        void insertStdOutLine(const QString& line)
        {
            // line already contains trailing '\n'
            mUI.consoleOutput->insertPlainText(line);

            QTextCursor cursor = mUI.consoleOutput->textCursor();
            cursor.movePosition(QTextCursor::End);
            mUI.consoleOutput->setTextCursor(cursor);
        }

        void notifyDone()
        {
            mUI.progressBar->setMinimum(0);
            mUI.progressBar->setMaximum(1);
            mUI.progressBar->setValue(1);

            mUI.buttonBox->setStandardButtons(QDialogButtonBox::Ok);
        }

    private:
        Ui_ProcessProgressDialog mUI;
};

SyncProcess::SyncProcess(QObject* parent):
    QObject(parent),

    mEnvironment(QProcessEnvironment::systemEnvironment()),
    mWorkingDirectory("./"),

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

void SyncProcess::setEnvironment(const QProcessEnvironment& env)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change environment!");

    mEnvironment = env;
}

void SyncProcess::setWorkingDirectory(const QString& dir)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change working directory!");

    mWorkingDirectory = dir;
}

void SyncProcess::setCancelRequestSource(bool* source)
{
    // Changing this while running is nasty but should work.
    // Especially in a synchronized single threaded environment.

    mCancelRequestSource = source;
}

void SyncProcess::run()
{
    mDiagnosticInfo = "";

    QProcess process(this);
    mDiagnosticInfo += QObject::tr("Starting process '%1'\n").arg(generateDescription());
    startQProcess(process);

    mRunning = true;

    while (!process.waitForFinished(mPollInterval))
    {
        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(thread())->processEvents(QEventLoop::AllEvents);

        if (wasCancelRequested())
        {
            mDiagnosticInfo += QObject::tr("Cancel was requested! Sending terminate signal to the process...\n");

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
                mDiagnosticInfo += QObject::tr("Process had to be killed! Didn't terminate after %1 msec of waiting.\n").arg(termWaited);
                process.kill();
                break;
            }
        }
    }

    mRunning = false;

    mStdOutContents = QString::fromLocal8Bit(process.readAllStandardOutput());
    mStdErrContents = QString::fromLocal8Bit(process.readAllStandardError());

    // TODO: We are duplicating data here!
    mDiagnosticInfo += "stdout:\n===============================\n" + QString(mStdOutContents) + QString("\n");
    mDiagnosticInfo += "stderr:\n===============================\n" + QString(mStdErrContents) + QString("\n");

    mExitCode = process.exitCode();
}

QDialog* SyncProcess::runWithDialog(QWidget* widgetParent, const QString& title,
    bool showCancelButton, bool closeAfterFinished, bool modal)
{
    ProcessProgressDialog* dialog = new ProcessProgressDialog(widgetParent);
    dialog->setModal(modal);

    QObject::connect(
        dialog, SIGNAL(rejected()),
        this, SLOT(cancel())
    );
    dialog->setWindowTitle(title);
    dialog->show();

    mDiagnosticInfo = "";

    QProcess process(this);
    process.setProcessChannelMode(QProcess::MergedChannels);
    mDiagnosticInfo += QObject::tr("Starting process '%1'\n").arg(generateDescription());
    startQProcess(process);

    mRunning = true;

    while (!process.waitForFinished(mPollInterval))
    {
        // pump the event queue, mainly because the user might want to cancel
        QAbstractEventDispatcher::instance(thread())->processEvents(QEventLoop::AllEvents);

        readAllChannelsIntoDialog(process, *dialog);

        if (wasCancelRequested())
        {
            mDiagnosticInfo += QObject::tr("Cancel was requested! Sending terminate signal to the process...\n");

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
                mDiagnosticInfo += QObject::tr("Process had to be killed! Didn't terminate after %1 msec of waiting.\n").arg(termWaited);
                process.kill();
                break;
            }
        }
    }

    readAllChannelsIntoDialog(process, *dialog);

    mRunning = false;

    mStdOutContents = process.readAllStandardOutput();
    mStdErrContents = process.readAllStandardError();

    // TODO: We are duplicating data here!
    mDiagnosticInfo += "stdout:\n===============================\n" + QString(mStdOutContents) + QString("\n");
    mDiagnosticInfo += "stderr:\n===============================\n" + QString(mStdErrContents) + QString("\n");

    mExitCode = process.exitCode();
    dialog->notifyDone();

    if (closeAfterFinished)
        dialog->done(QDialog::Accepted);

    return dialog;
}

void SyncProcess::cancel()
{
    mLocalCancelRequested = true;
}

bool SyncProcess::isRunning() const
{
    return mRunning;
}

void SyncProcess::setStdInFile(const QString& path)
{
    if (isRunning())
        throw SyncProcessException("Can't set stdin file when the process is running!");

    mStdInFile = path;
}

const QString& SyncProcess::getStdInFile() const
{
    return mStdInFile;
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

void SyncProcess::startQProcess(QProcess& process)
{
    const QString command = generateFullCommand();
    if (command.isEmpty())
        throw SyncProcessException("Cannot start process '" + generateDescription() + "'. The full command is '" + command + "'.");

    if (!mStdInFile.isEmpty())
        process.setStandardInputFile(mStdInFile);

    process.setProcessEnvironment(generateFullEnvironment());
    mDiagnosticInfo += QObject::tr("Starting process '%1'\n").arg(generateDescription());
    process.setWorkingDirectory(mWorkingDirectory);
    process.start(command, generateFullArguments());
    process.waitForStarted();

    if (process.state() != QProcess::Running)
        throw SyncProcessException("Starting process '" + generateDescription() + "' failed. The process is not in a running state.");
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

QProcessEnvironment SyncProcess::generateFullEnvironment() const
{
    return mEnvironment;
}

QString SyncProcess::generateDescription() const
{
    return mCommand + QString(" ") + mArguments.join(" ");
}

void SyncProcess::readAllChannelsIntoDialog(QProcess& process, ProcessProgressDialog& dialog)
{
    assert(process.processChannelMode() == QProcess::MergedChannels);
    process.setReadChannel(QProcess::StandardOutput);

    while (process.canReadLine())
    {
        const QString line = process.readLine();
        dialog.insertStdOutLine(line);
    }
}
