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

/// This class is never exposed, it is internal only
class ProcessProgressDialog;

/**
 * @brief Runs a process and pumps event queue of given thread
 */
class SyncProcess : public QObject
{
    Q_OBJECT

    public:
        SyncProcess(QObject* parent = 0);
        virtual ~SyncProcess();

        void setCommand(const QString& command);
        void setArguments(const QStringList& args);
        void setEnvironment(const QProcessEnvironment& env);
        void setWorkingDirectory(const QString& dir);

        void setCancelRequestSource(bool* source);

        void run();
        void runWithDialog(QWidget* widgetParent, const QString& title, bool showCancelButton = true, bool closeAfterFinished = false);

    public slots:
        void cancel();

    public:
        bool isRunning() const;

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
        bool* mCancelRequestSource;
        bool mLocalCancelRequested;

        int mExitCode;
        QString mStdOutContents;
        QString mStdErrContents;
        QString mDiagnosticInfo;
};

#endif
