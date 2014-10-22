/*
 * Copyright 2014 Red Hat Inc., Durham, North Carolina.
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

#include "RPMOpenHelper.h"
#include "ProcessHelpers.h"
#include "Exceptions.h"
#include <QDir>

RPMOpenHelper::RPMOpenHelper(const QString& path)
{
    mTempDir.setAutoRemove(true);

    SyncProcess proc;
    {
        const QFileInfo pathInfo(path);
        proc.setCommand(getRPMExtractPath());
        proc.setArguments(QStringList(pathInfo.absoluteFilePath()));
        proc.setWorkingDirectory(mTempDir.getPath());
    }

    proc.run();

    const QDir tempDir(mTempDir.getPath());

    if (proc.getExitCode() != 0)
    {
        mInputPath = "";
        mTailoringPath = "";

        throw RPMOpenHelperException(QString("Failed to extract given SCAP RPM, details follow:\n%1").arg(proc.getDiagnosticInfo()));
    }
    else
    {
        // Escape the escape to escape the escape!
        static QRegExp baselineRE("^\\.\\/usr\\/share\\/xml\\/scap\\/[^\\/]+\\/[^\\/]+$");
        static QRegExp tailoringRE("^\\.\\/usr\\/share\\/xml\\/scap\\/[^\\/]+\\/tailoring-xccdf\\.xml+$");
        static QRegExp inputRE("^\\.\\/usr\\/share\\/xml\\/scap\\/[^\\/]+\\/[^\\/]+\\-(xccdf|ds)\\.xml+$");

        QStringList lines = proc.getStdErrContents().split('\n', QString::SkipEmptyParts);
        for (QStringList::const_iterator it = lines.constBegin(); it != lines.constEnd(); ++it)
        {
            const QString& line = *it;

            // Skip cpio verbose info unrelated to file names
            if (!baselineRE.exactMatch(line))
                continue;

            // Tailoring is a very precise match, only try inputRE if tailoring doesn't match.
            // This is required because "tailoring-xccdf.xml" will match both tailoringRE and inputRE!

            if (tailoringRE.exactMatch(line))
                mTailoringPath = tempDir.absoluteFilePath(line);
            else if (inputRE.exactMatch(line))
                mInputPath = tempDir.absoluteFilePath(line);
        }
    }
}

RPMOpenHelper::~RPMOpenHelper()
{
    // temporary directory gets removed automatically
}

const QString& RPMOpenHelper::getInputPath() const
{
    return mInputPath;
}

bool RPMOpenHelper::hasTailoring() const
{
    return mTailoringPath.isEmpty();
}

const QString& RPMOpenHelper::getTailoringPath() const
{
    return mTailoringPath;
}

QString RPMOpenHelper::getRPMExtractPath()
{
    const QByteArray path = qgetenv("SCAP_WORKBENCH_RPM_EXTRACT_PATH");

    if (path.isEmpty())
        return SCAP_WORKBENCH_LOCAL_RPM_EXTRACT_PATH;
    else
        return path;
}
