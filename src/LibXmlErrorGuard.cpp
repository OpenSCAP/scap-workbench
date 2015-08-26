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

#include "LibXmlErrorGuard.h"
extern "C" {
    #include <libxml2/libxml/xmlerror.h>
    #include <stdarg.h>
}

LibXmlErrorGuard::LibXmlErrorGuard()
{
    xmlSetGenericErrorFunc(&errorMessage,(xmlGenericErrorFunc)(&LibXmlErrorGuard::libxmlErrorCallback));
}

LibXmlErrorGuard::~LibXmlErrorGuard()
{
    // set default libxml error handler
    xmlSetGenericErrorFunc(NULL, (xmlGenericErrorFunc)NULL);
}

const QString& LibXmlErrorGuard::getMessage() const
{
   return errorMessage;
}

bool LibXmlErrorGuard::isEmpty()
{
    return errorMessage.isEmpty();
}

void LibXmlErrorGuard::libxmlErrorCallback(QString* message, const char* format, ... )
{
    try
    {
        va_list args;
        va_start(args, format);
        QString newMessage = QString().vsprintf(format, args);
        va_end(args);
        message->append(newMessage);
    }
    catch(...)
    {
        ; // Possible exceptions aren't safe in C callback
    }
}
