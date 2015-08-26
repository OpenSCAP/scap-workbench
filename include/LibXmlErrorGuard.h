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
 */

#ifndef SCAP_WORKBENCH_LIB_XML_ERROR_GUARD_H_
#define SCAP_WORKBENCH_LIB_XML_ERROR_GUARD_H_
#include <QString>

/**
 * @brief Catch LibXML2 errors and store them
 *
 */
class LibXmlErrorGuard
{
public:
    /**
     * @brief Read LibXML2 errors using xmlSetGenericErrorFunc
     */
    LibXmlErrorGuard();

    /**
     * @brief Reset xmlGenericErrorFunc to default callback
     */
    ~LibXmlErrorGuard();

    const QString& getMessage() const;
    bool isEmpty();
private:
    static void libxmlErrorCallback(QString* message, const char* format, ...);
    QString errorMessage;
};

#endif // SCAP_WORKBENCH_LIB_XML_ERROR_GUARD_H_
