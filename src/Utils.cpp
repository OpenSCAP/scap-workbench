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
#include <QDesktopServices>
#include <QMessageBox>
#include <QCoreApplication>

#if defined(__APPLE__)
inline QDir _generateShareDir()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cdUp();
    dir.cd("Resources");
    dir.cd("share");
    dir.cd("scap-workbench");
    return dir;
}

inline QDir _generateDocDir()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cdUp();
    dir.cd("Resources");
    dir.cd("doc");
    return dir;
}

inline QDir _generateSSGDir()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cdUp();
    dir.cd("Resources");
    dir.cd("ssg");
    dir.cd("content");
    return dir;
}

inline QString _generateApplicationIconPath()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cdUp();
    dir.cd("Resources");
    dir.cd("share");
    dir.cd("pixmaps");
    return dir.absoluteFilePath("scap-workbench.png");
}

inline QString _generateSetSidPath()
{
    QDir dir(QCoreApplication::applicationDirPath());
    return dir.absoluteFilePath("setsid");
}
#elif defined(_WIN32)
inline QDir _generateShareDir()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cd("share");
    dir.cd("scap-workbench");
    return dir;
}

inline QDir _generateDocDir()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cd("doc");
    return dir;
}

inline QDir _generateSSGDir()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cd("ssg");
    dir.cd("content");
    return dir;
}

inline QString _generateApplicationIconPath()
{
    QDir dir(QCoreApplication::applicationDirPath());
    dir.cd("share");
    dir.cd("pixmaps");
    return dir.absoluteFilePath("scap-workbench.png");
}
#endif

const QDir& getShareDirectory()
{
#if defined(__APPLE__) || defined(_WIN32)
    static QDir ret(_generateShareDir());
    return ret;
#else
    static const QString installedPath = SCAP_WORKBENCH_SHARE;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_SHARE");
    static QDir ret(overriddenPath.isEmpty() ? installedPath : overriddenPath);

    return ret;
#endif
}

const QDir& getDocDirectory()
{
#if defined(__APPLE__) || defined(_WIN32)
    static QDir ret(_generateDocDir());
    return ret;
#else
    static const QString installedPath = SCAP_WORKBENCH_DOC;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_DOC");
    static QDir ret(overriddenPath.isEmpty() ? installedPath : overriddenPath);

    return ret;
#endif
}

const QDir& getSSGDirectory()
{
#if defined(__APPLE__) || defined(_WIN32)
    static QDir ret(_generateSSGDir());
    return ret;
#else
    static const QString installedPath = SCAP_WORKBENCH_SSG_DIRECTORY;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_SSG_DIRECTORY");
    static QDir ret(overriddenPath.isEmpty() ? installedPath : overriddenPath);

    return ret;
#endif
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

QPixmap getSharePixmap(const QString& fileName)
{
    const QString fullPath = getShareDirectory().absoluteFilePath(fileName);
    const QPixmap ret(fullPath);

    if (ret.isNull())
    {
        std::cerr << "getSharePixmap(..): Cannot create pixmap from '" << fullPath.toUtf8().constData() << "'." << std::endl;
    }

    return ret;
}

const QIcon& getApplicationIcon()
{
#if defined(__APPLE__) || defined(_WIN32)
    static const QString fullPath = _generateApplicationIconPath();
#else
    static const QString installedPath = SCAP_WORKBENCH_ICON;
    static const QString overriddenPath = qgetenv("SCAP_WORKBENCH_ICON");
    static const QString& fullPath = overriddenPath.isEmpty() ? installedPath : overriddenPath;
#endif

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

void openUrlGuarded(const QUrl& url)
{
    if (!QDesktopServices::openUrl(url))
        QMessageBox::warning(
            0, QObject::tr("Failed to open file in web browser!"),
            QObject::tr("Please check that your default browser is set to something sensible. "
                        "As a workaround, please open<br/><a href=\"%1\">%1</a><br/>manually.").arg(url.toString())
        );
}

const QString& getSetSidPath()
{
#if defined(__APPLE__)
    static QString ret(_generateSetSidPath());
    return ret;
#else
    static QString ret(SCAP_WORKBENCH_LOCAL_SETSID_PATH);
    return ret;
#endif
}
