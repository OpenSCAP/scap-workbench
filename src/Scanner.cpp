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

#include "Scanner.h"
#include <QThread>

Scanner::Scanner(QThread* thread):
    mThread(thread),
    mSession(0),
    mTarget(""),
    mOnlineRemediationEnabled(false)
{}

Scanner::~Scanner()
{}

void Scanner::setSession(struct xccdf_session* session)
{
    // TODO: assert that we are not running
    mSession = session;
}

void Scanner::setTarget(const QString& target)
{
    // TODO: assert that we are not running
    mTarget = target;
}

void Scanner::setOnlineRemediationEnabled(bool enabled)
{
    // TODO: assert that we are not running
    mOnlineRemediationEnabled = enabled;
}

void Scanner::signalCompletion(bool cancel)
{
    if (cancel)
        emit canceled();
    else
        emit finished();

    moveToThread(0);
    mThread->quit();
}