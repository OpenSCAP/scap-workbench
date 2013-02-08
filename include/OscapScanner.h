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

#ifndef SCAP_WORKBENCH_OSCAP_SCANNER_H_
#define SCAP_WORKBENCH_OSCAP_SCANNER_H_

#include "ForwardDecls.h"

#include "Scanner.h"
#include <QStringList>
#include <QProcess>
#include <QTemporaryFile>

class OscapScannerBase : public Scanner
{
    Q_OBJECT

    public:
        OscapScannerBase(QThread* thread, struct xccdf_session* session, const QString& target);
        virtual ~OscapScannerBase();

        virtual void cancel();

        virtual void getResults(QByteArray& destination);
        virtual void getReport(QByteArray& destination);
        virtual void getARF(QByteArray& destination);

    protected:
        int runProcessSync(const QString& cmd, const QStringList& args,
                           unsigned int pollInterval,
                           unsigned int termLimit,
                           QString& diagnosticInfo);

        QStringList buildCommandLineArgs(const QString& inputFile,
                                         const QString& resultFile,
                                         const QString& reportFile,
                                         const QString& arfFile);

        bool tryToReadLine(QProcess& process);

        bool mCancelRequested;

        QByteArray mResults;
        QByteArray mReport;
        QByteArray mARF;
};

class OscapScannerLocal : public OscapScannerBase
{
    Q_OBJECT

    public:
        OscapScannerLocal(QThread* thread, struct xccdf_session* session, const QString& target);
        virtual ~OscapScannerLocal();

        virtual void evaluate();
};

class OscapScannerRemoteSsh : public OscapScannerBase
{
    Q_OBJECT

    public:
        OscapScannerRemoteSsh(QThread* thread, struct xccdf_session* session, const QString& target);
        virtual ~OscapScannerRemoteSsh();

        virtual void evaluate();

    private:
        void establish();
        QString copyInputDataOver();

        QString mMasterSocket;
        QProcess* mMasterProcess;
};

#endif