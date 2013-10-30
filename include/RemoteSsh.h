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

#ifndef SCAP_WORKBENCH_REMOTE_SSH_H_
#define SCAP_WORKBENCH_REMOTE_SSH_H_

#include "ForwardDecls.h"
#include "ProcessHelpers.h"
#include <QObject>

class SshConnection : public QObject
{
    Q_OBJECT

    public:
        SshConnection(QObject* parent);
        ~SshConnection();

        /**
         * @brief Sets ssh target in the form of username@hostname
         */
        void setTarget(const QString& target);
        const QString& getTarget() const;

        void setPort(unsigned short port);
        unsigned short getPort() const;

        void setCancelRequestSource(bool* source);

        void connect();
        void disconnect();
        bool isConnected() const;

        const QString& _getMasterSocket() const;
        const QProcessEnvironment& _getEnvironment() const;

    private:
        QString mTarget;
        unsigned short mPort;

        QString mMasterSocket;
        QProcessEnvironment mEnvironment;

        bool mConnected;

        bool* mCancelRequestSource;
};

class SshSyncProcess : public SyncProcess
{
    Q_OBJECT

    public:
        SshSyncProcess(SshConnection& connection, QObject* parent = 0);
        virtual ~SshSyncProcess();

    protected:
        virtual QString generateFullCommand() const;
        virtual QStringList generateFullArguments() const;
        virtual QProcessEnvironment generateFullEnvironment() const;
        virtual QString generateDescription() const;

        SshConnection& mSshConnection;
};

enum ScpDirection
{
    SD_LOCAL_TO_REMOTE,
    SD_REMOTE_TO_LOCAL
};

class ScpSyncProcess : public SyncProcess
{
    Q_OBJECT

    public:
        ScpSyncProcess(SshConnection& connection, QObject* parent = 0);
        virtual ~ScpSyncProcess();

        void setDirection(ScpDirection direction);
        ScpDirection getDirection() const;

        void setLocalPath(const QString& path);
        const QString& getLocalPath() const;

        void setRemotePath(const QString& path);
        const QString& getRemotePath() const;

    protected:
        virtual QString generateFullCommand() const;
        virtual QStringList generateFullArguments() const;
        virtual QProcessEnvironment generateFullEnvironment() const;
        virtual QString generateDescription() const;

        ScpDirection mScpDirection;
        QString mLocalPath;
        QString mRemotePath;
        SshConnection& mSshConnection;
};
#endif
