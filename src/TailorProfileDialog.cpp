/*
 * Copyright 2013 - 2014 Red Hat Inc., Durham, North Carolina.
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

#include "TailorProfileDialog.h"

TailorProfileDialog::TailorProfileDialog(const QString& startId, bool xccdf12, QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);
    mUI.idLineEdit->setText(startId);

    if (xccdf12)
    {
        // regex taken from XCCDF 1.2 official XSD
        mUI.idLineEdit->setValidator(
            new QRegExpValidator(QRegExp("xccdf_[^_]+_profile_.+"), mUI.idLineEdit));

        // TODO: This is definitely not ideal, people can still input invalid text
        // if they really try hard
    }

    mUI.xccdf12Warning->setVisible(xccdf12);
}

TailorProfileDialog::~TailorProfileDialog()
{}

QString TailorProfileDialog::getProfileID() const
{
    return mUI.idLineEdit->text();
}
