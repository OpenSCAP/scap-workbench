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

#include <QDir>
#include <iostream>

static bool recursiveRemoveDir(const QString& dirName)
{
    // Adapted code from:
    // http://john.nachtimwald.com/2010/06/08/qt-remove-directory-and-its-contents/

    bool result = true;
    QDir dir(dirName);

    if (dir.exists(dirName))
    {
        Q_FOREACH(QFileInfo info, dir.entryInfoList(QDir::NoDotAndDotDot | QDir::System | QDir::Hidden  | QDir::AllDirs | QDir::Files, QDir::DirsFirst))
        {
            if (info.isDir())
                result = recursiveRemoveDir(info.absoluteFilePath());
            else
                result = QFile::remove(info.absoluteFilePath());

            if (!result)
                return result;
        }
        result = dir.rmdir(dirName);
    }

    return result;
}

TemporaryDir::TemporaryDir():
    mAutoRemove(true)
{}

TemporaryDir::~TemporaryDir()
{
    if (!mPath.isEmpty() && mAutoRemove)
    {
        if (!recursiveRemoveDir(mPath))
        {
            // We don't throw on destruction! The worst thing that can happen
            // is leftover files which is not a big deal anyway.

            std::cerr << "Failed to remove temporary directory '" << mPath.toUtf8().constData() << "'." << std::endl;
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

// nextRand adapted from from QTemporaryDir from Qt5, licensed under LGPL2.1+

// Copyright (C) 2014 Digia Plc and/or its subsidiary(-ies).
// Contact: http://www.qt-project.org/legal
//
// GNU Lesser General Public License Usage
// Alternatively, this file may be used under the terms of the GNU Lesser
// General Public License version 2.1 or version 3 as published by the Free
// Software Foundation and appearing in the file LICENSE.LGPLv21 and
// LICENSE.LGPLv3 included in the packaging of this file. Please review the
// following information to ensure the GNU Lesser General Public License
// requirements will be met: https://www.gnu.org/licenses/lgpl.html and
// http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html.
//
// In addition, as a special exception, Digia gives you certain additional
// rights. These rights are described in the Digia Qt LGPL Exception
// version 1.1, included in the file LGPL_EXCEPTION.txt in this package.

static int nextRand(int& v)
{
    int r = v % 62;
    v /= 62;
    if (v < 62)
        v = qrand();
    return r;
}

void TemporaryDir::ensurePath() const
{
    static const char letters[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

    if (mPath.isEmpty())
    {
        QString dirName;
        while (true)
        {
            dirName = "";

            int v = qrand();
            dirName += letters[nextRand(v)];
            dirName += letters[nextRand(v)];
            dirName += letters[nextRand(v)];
            dirName += letters[nextRand(v)];
            dirName += letters[nextRand(v)];
            dirName += letters[nextRand(v)];

            if (QDir::temp().mkdir(dirName))
                break;
        }

        const QDir dir(QDir::temp().absoluteFilePath(dirName));

        if (!dir.exists())
            throw TemporaryDirException(
                QString("Failed to create temporary directory. mkdir succeeded "
                    "but the directory does not exist!")
            );

        mPath = dir.absolutePath();
    }
}
