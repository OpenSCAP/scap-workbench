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

#ifndef SCAP_WORKBENCH_EXCEPTIONS_H_
#define SCAP_WORKBENCH_EXCEPTIONS_H_

#include "ForwardDecls.h"

#include <stdexcept>
#include <string>

#define SCAP_WORKBENCH_SIMPLE_EXCEPTION(NAME, PREFIX) \
class NAME : public std::runtime_error \
{ \
    public: \
        NAME(const QString& msg): \
            std::runtime_error(std::string(PREFIX) + std::string(msg.toUtf8().data())) \
        {} \
\
        virtual ~NAME() throw()\
        {} \
};

SCAP_WORKBENCH_SIMPLE_EXCEPTION(MainWindowException,
    "There was a problem with MainWindow!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(RuleResultsTreeException,
    "There was a problem with RuleResultsTree!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(ScanningSessionException,
    "There was a problem with ScanningSession!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(SyncProcessException,
    "There was a problem with SyncProcess!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(SshConnectionException,
    "There was a problem with SshConnection!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(TailoringWindowException,
    "There was a problem with TailoringWindow!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(TemporaryDirException,
    "There was a problem with TemporaryDir!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(OscapScannerRemoteSshException,
    "There was a problem with OscapScannerRemoteSsh!\n");

SCAP_WORKBENCH_SIMPLE_EXCEPTION(RPMOpenHelperException,
    "There was a problem with RPMOpenHelper!\n");

#endif
