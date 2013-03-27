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

DiagnosticsDialog::DiagnosticsDialog(QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);
}

DiagnosticsDialog::~DiagnosticsDialog()
{}

void DiagnosticsDialog::clear()
{
    // TODO
}

void DiagnosticsDialog::infoMessage(const QString& message)
{
    QStringList columns;
    columns.append("info");
    columns.append(message);

    QTreeWidgetItem* item = new QTreeWidgetItem(columns);
    item->setForeground(0, QBrush(Qt::gray));
    mUI.messages->addTopLevelItem(item);
}

void DiagnosticsDialog::warningMessage(const QString& message)
{
    QStringList columns;
    columns.append("warning");
    columns.append(message);

    QTreeWidgetItem* item = new QTreeWidgetItem(columns);
    item->setForeground(0, QBrush(Qt::yellow));
    mUI.messages->addTopLevelItem(item);

    // warning message is important, make sure the diagnostics are shown
    show();
}

void DiagnosticsDialog::errorMessage(const QString& message)
{
    QStringList columns;
    columns.append("error");
    columns.append(message);

    QTreeWidgetItem* item = new QTreeWidgetItem(columns);
    item->setForeground(0, QBrush(Qt::red));
    mUI.messages->addTopLevelItem(item);

    // error message is important, make sure the diagnostics are shown
    show();
}
