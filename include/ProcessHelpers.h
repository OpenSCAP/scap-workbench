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

#ifndef SCAP_WORKBENCH_PROCESS_HELPERS_H_
#define SCAP_WORKBENCH_PROCESS_HELPERS_H_

#include "ForwardDecls.h"
#include <QObject>
#include <QString>
#include <QStringList>
#include <QProcessEnvironment>
#include <QDialog>

/// This class is never exposed, it is internal only
class ProcessProgressDialog;

/**
 * @brief Runs a process and pumps event queue of given thread
 */
class SyncProcess : public QObject
{
    Q_OBJECT

    public:
        explicit SyncProcess(QObject* parent = 0);
        virtual ~SyncProcess();

        /**
         * @brief Sets the main command (without arguments)
         *
         * This always needs to be called before the SyncProcess::run method is called.
         * Command is a strictly required property!
         */
        void setCommand(const QString& command);

        /**
         * @brief Sets all passed arguments
         *
         * Default is empty.
         */
        void setArguments(const QStringList& args);

        /**
         * @brief Sets the running environment
         *
         * Default is to inherit the system environment.
         */
        void setEnvironment(const QProcessEnvironment& env);

        /**
         * @brief Sets the working directory
         *
         * Default is current working directory ("./")
         */
        void setWorkingDirectory(const QString& dir);

        /**
         * @brief Sets external cancel request source (indirect)
         *
         * The only reason this exists is to accommodate the interface of OscapScannerBase.
         * We should move to the cancel() slot in the future.
         * @todo Get rid of this non-sense
         */
        void setCancelRequestSource(bool* source);

        /**
         * @brief Runs the SyncProcess, blocks until the process exits
         *
         * @see SyncProcess::isRunning
         * @see SyncProcess::getExitCode
         */
        void run();

        /**
         * @brief Similar to SyncProcess::run, runs the process and shows a dialog of the progress
         *
         * This method has a limitation compared to SyncProcess::run in the fact that it does
         * not fill stdout and stderr outputs with the correct data. It's reading all output
         * and immediatelly showing it in the dialog, stdout and stderr will be empty after
         * this method finishes!
         */
        QDialog* runWithDialog(QWidget* widgetParent, const QString& title,
            bool showCancelButton = true, bool closeAfterFinished = false, bool modal = true);

    public slots:
        /**
         * @brief Requests cancellation
         *
         * Cancellation will not happen immediately! First SIGTERM is sent to the process.
         * If the process fails to respond and exit in 3 seconds SIGKILL is sent.
         */
        void cancel();

    public:
        bool isRunning() const;

        void setStdInFile(const QString& path);
        const QString& getStdInFile() const;

        int getExitCode() const;
        const QString& getStdOutContents() const;
        const QString& getStdErrContents() const;
        const QString& getDiagnosticInfo() const;

    protected:
        void startQProcess(QProcess& process);
        bool wasCancelRequested() const;

        virtual QString generateFullCommand() const;
        virtual QStringList generateFullArguments() const;
        virtual QProcessEnvironment generateFullEnvironment() const;
        virtual QString generateDescription() const;

        void readAllChannelsIntoDialog(QProcess& process, ProcessProgressDialog& dialog);

        QString mCommand;
        QStringList mArguments;
        QProcessEnvironment mEnvironment;
        QString mWorkingDirectory;

        /// How often do we poll for status, in msec
        unsigned int mPollInterval;
        /// How long will we wait for the process to exit after term is signaled, in msec
        unsigned int mTermLimit;

        bool mRunning;
        /// A crappy makeshift synchronization primitive. We should abolish this in the future.
        /// It works fine for now because we only change it from within the Qt event loop.
        bool* mCancelRequestSource;
        /// Was cancellation requested locally (cancel() slot)
        bool mLocalCancelRequested;

        QString mStdInFile;
        int mExitCode;
        QString mStdOutContents;
        QString mStdErrContents;
        QString mDiagnosticInfo;
};

#endif
