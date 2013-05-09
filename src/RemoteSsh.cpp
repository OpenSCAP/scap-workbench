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

    mConnected(false),
    mCancelRequestSource(0)
{}

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
        proc.setCancelRequestSource(mCancelRequestSource);
        proc.run();

        mMasterSocket = proc.getStdOutContents().trimmed() + "/ssh_socket";
    }
    catch (const SyncProcessException& e)
    {
        throw SshConnectionException(
            QString("Failed to create a temporary directory on local machine! Exception was: %1").arg(e.what()));
    }

    if (mCancelRequestSource && *mCancelRequestSource)
        return;

    try
    {
        QStringList args;
        args.append("-M");
        args.append("-f");
        args.append("-N");

        args.append("-o"); args.append(QString("ControlPath=%1").arg(mMasterSocket));

        // TODO: sanitize input?
        args.append(mTarget);

        SyncProcess proc(this);
        proc.setCommand("ssh");
        proc.setArguments(args);
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
            QString("Failed to create SSH master socket! Exception was: %1").arg(e.what()));
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
        proc.setCommand("ssh");
        proc.setArguments(args);
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
