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

#ifndef SCAP_WORKBENCH_UTILS_H_
#define SCAP_WORKBENCH_UTILS_H_

#include "ForwardDecls.h"

#include <QString>
#include <QDir>
#include <QIcon>
#include <QUrl>

/**
 * @brief Retrieves QDir representing the share directory
 *
 * For installed scap-workbench the output's path usually looks like this:
 * "$INSTALL_PREFIX/share/scap-workbench", e.g.: /usr/share/scap-workbench
 *
 * If workbench has not been installed and is being run using the runwrapper.sh
 * script, the path will be different and will point to the data location
 * in the repository.
 *
 * Avoid using hardcoded paths in the codebase and always use paths relative
 * to the share path.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
const QDir& getShareDirectory();

/**
 * @brief Retrieves QDir representing the doc directory
 *
 * For installed scap-workbench the output's path usually looks like this:
 * "$INSTALL_PREFIX/share/doc/scap-workbench", e.g.: /usr/share/doc/scap-workbench
 *
 * If workbench has not been installed and is being run using the runwrapper.sh
 * script, the path will be different and will point to the data location
 * in the repository.
 *
 * Avoid using hardcoded paths in the codebase and always use paths relative
 * to the doc path.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
const QDir& getDocDirectory();

/**
 * @brief Retrieves QDir representing the SSG directory
 *
 * For installed scap-workbench the output's path usually looks like this:
 * "/$INSTALL_PREFIX/share/xml/scap/ssg", e.g.: /usr/share/xml/scap/ssg
 *
 * Avoid using hardcoded paths in the codebase and always use paths relative
 * to the doc path.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
const QDir& getSSGDirectory();

/**
 * @brief Constructs a QIcon from image of given filename
 *
 * This function looks for the file in the icon folder in workbench's share path.
 * Using this function to get an icon is preferable to constructing it manually.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 * @note This function will write a warning to stderr in case the icon cannot be loaded.
 */
QIcon getShareIcon(const QString& fileName);
QPixmap getSharePixmap(const QString& fileName);

/**
 * @brief Retrieves the global application icon
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 * @note This function will write a warning to stderr in case the icon cannot be loaded.
 */
const QIcon& getApplicationIcon();

/**
 * @brief Retrieves the QDir representing the directory with translations
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
const QDir& getShareTranslationDirectory();

/**
 * @brief Calls QDesktopServices::openUrl, shows a message box in case of failure
 *
 * @param url URL to open
 */
void openUrlGuarded(const QUrl& url);

/**
 * @brief Retrieves path to setsid
 */
const QString& getSetSidPath();

#endif
