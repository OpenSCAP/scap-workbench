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

#include "TemporaryDir.h"
#include "ProcessHelpers.h"
#include "Exceptions.h"

TemporaryDir::TemporaryDir():
    mAutoRemove(true)
{}

TemporaryDir::~TemporaryDir()
{
    if (!mPath.isEmpty() && mAutoRemove)
    {
        SyncProcess proc;
        proc.setCommand(SCAP_WORKBENCH_LOCAL_RM);
        QStringList args;
        args.push_back("-rf"); args.push_back(mPath);
        proc.setArguments(args);
        proc.run();

        if (proc.getExitCode() != 0)
        {
            // We don't throw on destruction! The worst thing that can happen
            // is leftover files which is not a big deal anyway.

            // FIXME: Debug printout?
        }
    }
}

void TemporaryDir::setAutoRemove(const bool autoRemove)
{
    mAutoRemove = autoRemove;
}

bool TemporaryDir::getAutoRemove() const
{
    return mAutoRemove;
}

const QString& TemporaryDir::getPath() const
{
    ensurePath();
    return mPath;
}

void TemporaryDir::ensurePath() const
{
    if (mPath.isEmpty())
    {
        SyncProcess proc;
        proc.setCommand(SCAP_WORKBENCH_LOCAL_MKTEMP);
        proc.setArguments(QStringList("-d"));
        proc.run();

        if (proc.getExitCode() != 0)
        {
            throw TemporaryDirException(
                QString("Failed to create temporary directory.\n"
                    "Diagnostic info:\n%1").arg(proc.getDiagnosticInfo())
            );
        }

        mPath = proc.getStdOutContents().trimmed();
    }
}
