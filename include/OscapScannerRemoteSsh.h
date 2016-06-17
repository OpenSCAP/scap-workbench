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

#ifndef SCAP_WORKBENCH_OSCAP_SCANNER_REMOTE_SSH_H_
#define SCAP_WORKBENCH_OSCAP_SCANNER_REMOTE_SSH_H_

#include "ForwardDecls.h"
#include "OscapScannerBase.h"
#include "RemoteSsh.h"

class OscapScannerRemoteSsh : public OscapScannerBase
{
    Q_OBJECT

    public:
        static void splitTarget(const QString& in, QString& target, short& port);

        OscapScannerRemoteSsh();
        virtual ~OscapScannerRemoteSsh();

        virtual void setTarget(const QString& target);
        virtual void setSession(ScanningSession* session);

        virtual QStringList getCommandLineArgs() const;
        virtual void evaluate();

    private:
        void ensureConnected();

        QString copyFileOver(const QString& localPath);
        QString copyInputFileOver();

        QString createRemoteTemporaryFile(bool cancelOnFailure = true);
        QString createRemoteTemporaryDirectory(bool cancelOnFailure = true);

        QString readRemoteFile(const QString& path, const QString& desc);

        void removeRemoteFile(const QString& path, const QString& desc);
        void removeRemoteDirectory(const QString& path, const QString& desc);

        SshConnection mSshConnection;
};

#endif
