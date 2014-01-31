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

#include "RemoteSsh.h"
#include "ProcessHelpers.h"
#include "Exceptions.h"

#include <QFileInfo>
#include <QDir>

SshConnection::SshConnection(QObject* parent):
    QObject(parent),

    mTarget(""),
    mPort(22),

    mEnvironment(QProcessEnvironment::systemEnvironment()),
    mConnected(false),
    mCancelRequestSource(0)
{
    mEnvironment.remove("SSH_TTY");
    mEnvironment.insert("DISPLAY", ":0");
}

SshConnection::~SshConnection()
{
    if (isConnected())
        disconnect();
}

void SshConnection::setTarget(const QString& target)
{
    if (isConnected())
        throw SshConnectionException(
            "Can't change target after SSH has already been connected");

    mTarget = target;
}

const QString& SshConnection::getTarget() const
{
    return mTarget;
}

void SshConnection::setPort(unsigned short port)
{
    if (isConnected())
        throw SshConnectionException(
            "Can't change port after SSH has already been connected");

    mPort = port;
}

unsigned short SshConnection::getPort() const
{
    return mPort;
}

void SshConnection::setCancelRequestSource(bool* source)
{
    if (isConnected())
        throw SshConnectionException(
            "Can't change cancel request source after SSH has already been connected");

    mCancelRequestSource = source;
}

void SshConnection::connect()
{
    if (isConnected())
        throw SshConnectionException(
            "Already connected, disconnect first!");

    try
    {
        SyncProcess proc(this);
        proc.setCommand("mktemp");
        proc.setArguments(QStringList("-d"));
        proc.setEnvironment(mEnvironment);
        proc.setCancelRequestSource(mCancelRequestSource);
        proc.run();

        mMasterSocket = proc.getStdOutContents().trimmed() + "/ssh_socket";
    }
    catch (const SyncProcessException& e)
    {
        throw SshConnectionException(
            QString("Failed to create a temporary directory on local machine! Exception was: %1").arg(QString::fromUtf8(e.what())));
    }

    if (mCancelRequestSource && *mCancelRequestSource)
        return;

    try
    {
        QStringList args;
        args.append(SCAP_WORKBENCH_LOCAL_SSH_PATH);
        args.append("-M");
        args.append("-f");
        args.append("-N");

        args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));

        args.append("-p"); args.append(QString::number(mPort));
        // TODO: sanitize input?
        args.append(mTarget);

        SyncProcess proc(this);
        proc.setCommand(SCAP_WORKBENCH_LOCAL_SETSID_PATH);
        proc.setArguments(args);
        proc.setEnvironment(mEnvironment);
        proc.setCancelRequestSource(mCancelRequestSource);
        proc.run();

        if (proc.getExitCode() != 0)
        {
            throw SshConnectionException(
                QString("Failed to create SSH master socket! Diagnostic info: %1").arg(proc.getDiagnosticInfo()));
        }
    }
    catch (const SyncProcessException& e)
    {
        throw SshConnectionException(
            QString("Failed to create SSH master socket! Exception was: %1").arg(QString::fromUtf8(e.what())));
    }

    if (mCancelRequestSource && *mCancelRequestSource)
        return;

    mConnected = true;
}

void SshConnection::disconnect()
{
    if (!isConnected())
        throw SshConnectionException(
            "Not connected, makes no sense to disconnect!");

    {
        QStringList args;
        args.append("-S"); args.append(mMasterSocket);

        args.append("-O"); args.append("exit");
        args.append(mTarget);

        SyncProcess proc(this);
        proc.setCommand(SCAP_WORKBENCH_LOCAL_SSH_PATH);
        proc.setArguments(args);
        proc.setEnvironment(mEnvironment);
        proc.run();
    }

    // delete the parent temporary directory we created
    QFileInfo socketFile(mMasterSocket);
    QDir socketDir = socketFile.dir();

    if (!socketDir.rmdir(socketDir.absolutePath()))
    {
        throw SshConnectionException(
            QString("Failed to remove temporary directory hosting the ssh "
                    "connection socket."));
    }

    mConnected = false;
}

bool SshConnection::isConnected() const
{
    return mConnected;
}

const QString& SshConnection::_getMasterSocket() const
{
    return mMasterSocket;
}

const QProcessEnvironment& SshConnection::_getEnvironment() const
{
    return mEnvironment;
}

SshSyncProcess::SshSyncProcess(SshConnection& connection, QObject* parent):
    SyncProcess(parent),

    mSshConnection(connection)
{}

SshSyncProcess::~SshSyncProcess()
{}

QString SshSyncProcess::generateFullCommand() const
{
    return SCAP_WORKBENCH_LOCAL_SSH_PATH;
}

QStringList SshSyncProcess::generateFullArguments() const
{
    if (!mSshConnection.isConnected())
        mSshConnection.connect();

    QStringList args;

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));
    args.append(mSshConnection.getTarget());
    args.append(SyncProcess::generateFullCommand() + QString(" ") + SyncProcess::generateFullArguments().join(" "));

    return args;
}

QProcessEnvironment SshSyncProcess::generateFullEnvironment() const
{
    if (!mSshConnection.isConnected())
        mSshConnection.connect();

    return mSshConnection._getEnvironment();
}

QString SshSyncProcess::generateDescription() const
{
    return QString("Remote command '%1' on machine '%2'").arg(SyncProcess::generateDescription()).arg(mSshConnection.getTarget());
}

ScpSyncProcess::ScpSyncProcess(SshConnection& connection, QObject* parent):
    SyncProcess(parent),

    mScpDirection(SD_LOCAL_TO_REMOTE),
    mSshConnection(connection)
{}

ScpSyncProcess::~ScpSyncProcess()
{}

void ScpSyncProcess::setDirection(ScpDirection direction)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change scp direction!");

    mScpDirection = direction;
}

ScpDirection ScpSyncProcess::getDirection() const
{
    return mScpDirection;
}

void ScpSyncProcess::setLocalPath(const QString& path)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change local path!");

    mLocalPath = path;
}

const QString& ScpSyncProcess::getLocalPath() const
{
    return mLocalPath;
}

void ScpSyncProcess::setRemotePath(const QString& path)
{
    if (isRunning())
        throw SyncProcessException("Already running, can't change remote path!");

    mRemotePath = path;
}

const QString& ScpSyncProcess::getRemotePath() const
{
    return mRemotePath;
}

QString ScpSyncProcess::generateFullCommand() const
{
    return "scp";
}

QStringList ScpSyncProcess::generateFullArguments() const
{
    if (!mSshConnection.isConnected())
        mSshConnection.connect();

    QStringList args;

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));

    if (mScpDirection == SD_LOCAL_TO_REMOTE)
    {
        args.append(mLocalPath);
        args.append(QString("%1:%2").arg(mSshConnection.getTarget()).arg(mRemotePath));
    }
    else if (mScpDirection == SD_REMOTE_TO_LOCAL)
    {
        args.append(QString("%1:%2").arg(mSshConnection.getTarget()).arg(mRemotePath));
        args.append(mLocalPath);
    }
    else
    {
        throw SyncProcessException("ScpSyncProcess has unknown direction. Can't generate full arguments.");
    }

    return args;
}

QProcessEnvironment ScpSyncProcess::generateFullEnvironment() const
{
    if (!mSshConnection.isConnected())
        mSshConnection.connect();

    return mSshConnection._getEnvironment();
}

QString ScpSyncProcess::generateDescription() const
{
    if (mScpDirection == SD_LOCAL_TO_REMOTE)
    {
        return QString("Copy file '%1' on local machine to file '%2' on remote machine '%3'").arg(mLocalPath).arg(mRemotePath).arg(mSshConnection.getTarget());
    }
    else if (mScpDirection == SD_REMOTE_TO_LOCAL)
    {
        return QString("Copy file '%1' on remote machine '%2' to local file '%3'").arg(mRemotePath).arg(mSshConnection.getTarget().arg(mLocalPath));
    }
    else
    {
        return QString("ScpSyncProcess with unknown direction.");
    }
}
