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

#include "Utils.h"
#include <iostream>

const QDir& getShareDirectory()
{
    static const QString installedPath = SCAP_WORKBENCH_SHARE;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_SHARE");
    static QDir ret(overriddenPath.isEmpty() ? installedPath : overriddenPath);

    return ret;
}

const QDir& getDocDirectory()
{
    static const QString installedPath = SCAP_WORKBENCH_DOC;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_DOC");
    static QDir ret(overriddenPath.isEmpty() ? installedPath : overriddenPath);

    return ret;
}

QIcon getShareIcon(const QString& fileName)
{
    const QString fullPath = getShareDirectory().absoluteFilePath(fileName);
    const QIcon ret(fullPath);

    if (ret.pixmap(1, 1).isNull())
    {
        std::cerr << "getShareIcon(..): Cannot create pixmap from icon '" << fullPath.toUtf8().constData() << "'." << std::endl;
    }

    return ret;
}

const QIcon& getApplicationIcon()
{
    static const QString installedPath = SCAP_WORKBENCH_ICON;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_ICON");
    static const QString& fullPath = overriddenPath.isEmpty() ? installedPath : overriddenPath;
    static const QIcon ret = QIcon(fullPath);

    if (ret.pixmap(1, 1).isNull())
    {
        std::cerr << "getApplicationIcon(): Cannot create pixmap from icon '" << fullPath.toUtf8().constData() << "'." << std::endl;
    }

    return ret;
}

const QDir& getShareTranslationDirectory()
{
    static const QDir ret(getShareDirectory().absoluteFilePath("i18n"));
    return ret;
}
