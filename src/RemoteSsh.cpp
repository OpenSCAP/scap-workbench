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
#include "Utils.h"

#include <QFileInfo>
#include <QDir>
#include <QCoreApplication>

SshConnection::SshConnection(QObject* parent):
    QObject(parent),

    mTarget(""),
    mPort(22),

    mSocketDir(0),

    mEnvironment(QProcessEnvironment::systemEnvironment()),
    mConnected(false),
    mCancelRequestSource(0)
{
    mEnvironment.remove("SSH_TTY");
    mEnvironment.insert("DISPLAY", ":0");

#if defined(__APPLE__)
    static const QDir dir(QCoreApplication::applicationDirPath());
    mEnvironment.insert("SSH_ASKPASS", dir.absoluteFilePath("scap-workbench-osx-ssh-askpass.sh"));
#elif defined(WIN32)
    static const QDir dir(QCoreApplication::applicationDirPath());
    mEnvironment.insert("SSH_ASKPASS", dir.absoluteFilePath("win-ssh-askpass.exe"));
#endif
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
        if (mSocketDir)
        {
            delete mSocketDir;
            mSocketDir = 0;
        }

        mSocketDir = new TemporaryDir();
        mMasterSocket = mSocketDir->getPath() + "/ssh_socket";
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
#ifdef SCAP_WORKBENCH_LOCAL_SETSID_FOUND
#   ifdef SCAP_WORKBENCH_LOCAL_SETSID_SUPPORTS_WAIT
        args.append("--wait");
#   endif
        args.append(SCAP_WORKBENCH_LOCAL_SSH_PATH);
#endif

        args.append("-M"); // place ssh client into "master" mode for connection sharing
        args.append("-f"); // requests ssh to go to background before command execution
        args.append("-N"); // do not execute a remote command (yet)

        // send keep alive null messages every 60 seconds to make sure the connection stays alive
        args.append("-o"); args.append(QString("ServerAliveInterval=%1").arg(60));
        args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));
        args.append("-p"); args.append(QString::number(mPort));
        // TODO: sanitize input?
        args.append(mTarget);

        SyncProcess proc(this);
#ifdef SCAP_WORKBENCH_LOCAL_SETSID_FOUND
        proc.setCommand(getSetSidPath());
#else
        proc.setCommand(SCAP_WORKBENCH_LOCAL_SSH_PATH);
#endif
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
#ifdef SCAP_WORKBENCH_LOCAL_SETSID_FOUND
#   ifdef SCAP_WORKBENCH_LOCAL_SETSID_SUPPORTS_WAIT
        args.append("--wait");
#   endif
        args.append(SCAP_WORKBENCH_LOCAL_SSH_PATH);
#endif

        args.append("-S"); args.append(mMasterSocket);
        args.append("-p"); args.append(QString::number(mPort));
        args.append("-O"); args.append("exit");
        args.append(mTarget);

        SyncProcess proc(this);
#ifdef SCAP_WORKBENCH_LOCAL_SETSID_FOUND
        proc.setCommand(getSetSidPath());
#else
        proc.setCommand(SCAP_WORKBENCH_LOCAL_SSH_PATH);
#endif
        proc.setArguments(args);
        proc.setEnvironment(mEnvironment);
        proc.run();
    }

    // delete the parent temporary directory we created
    if (mSocketDir)
    {
        delete mSocketDir;
        mSocketDir = 0;
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
#ifdef SCAP_WORKBENCH_LOCAL_SETSID_FOUND
    return getSetSidPath();
#else
    return SCAP_WORKBENCH_LOCAL_SSH_PATH;
#endif
}

QStringList SshSyncProcess::generateFullArguments() const
{
    if (!mSshConnection.isConnected())
        mSshConnection.connect();

    QStringList args;
#ifdef SCAP_WORKBENCH_LOCAL_SETSID_FOUND
#   ifdef SCAP_WORKBENCH_LOCAL_SETSID_SUPPORTS_WAIT
        args.append("--wait");
#   endif
    args.append(SCAP_WORKBENCH_LOCAL_SSH_PATH);
#endif

    args.append("-o"); args.append(QString("ControlPath=%1").arg(mSshConnection._getMasterSocket()));
    args.append("-p"); args.append(QString::number(mSshConnection.getPort()));
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
