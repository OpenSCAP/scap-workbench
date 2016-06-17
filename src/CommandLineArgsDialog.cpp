/*
 * Copyright 2016 Red Hat Inc., Durham, North Carolina.
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

#include "CommandLineArgsDialog.h"

#include <QAbstractEventDispatcher>
#include <QApplication>
#include <QClipboard>

CommandLineArgsDialog::CommandLineArgsDialog(QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.clipboardButton, SIGNAL(clicked()),
        this, SLOT(copyToClipboard())
    );

    QObject::connect(
        mUI.closeButton, SIGNAL(clicked()),
        this, SLOT(hide())
    );
}

CommandLineArgsDialog::~CommandLineArgsDialog()
{}

void CommandLineArgsDialog::setArgs(const QStringList& args)
{
    mUI.args->setText(args.join(" "));
}

void CommandLineArgsDialog::copyToClipboard()
{
    const QString fullLog = mUI.args->toPlainText();
    QClipboard* clipboard = QApplication::clipboard();
    clipboard->setText(fullLog);
}
