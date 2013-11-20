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

#include "DiagnosticsDialog.h"
#include <iostream>

DiagnosticsDialog::DiagnosticsDialog(QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.closeButton, SIGNAL(released()),
        this, SLOT(hide())
    );
}

DiagnosticsDialog::~DiagnosticsDialog()
{}

void DiagnosticsDialog::clear()
{
    mUI.messages->clear();
}

void DiagnosticsDialog::infoMessage(const QString& message)
{
    pushMessage("[info] " + message);
}

void DiagnosticsDialog::warningMessage(const QString& message)
{
    pushMessage("[warn] " + message);

    // warning message is important, make sure the diagnostics are shown
    show();
}

void DiagnosticsDialog::errorMessage(const QString& message)
{
    pushMessage("[err ] " + message, true);

    // error message is important, make sure the diagnostics are shown
    show();
}

void DiagnosticsDialog::pushMessage(const QString& fullMessage, const bool error)
{
    char stime[11];
    stime[10] = '\0';

    time_t rawtime;
    struct tm* timeinfo;

    time(&rawtime);
    timeinfo = localtime(&rawtime);

    strftime(stime, 10, "%H:%M:%S", timeinfo);

    const QString outMessage = QString(stime) + " | " + fullMessage;

    std::cerr << outMessage.toUtf8().constData() << std::endl;

    mUI.messages->append(outMessage + "\n");
}
