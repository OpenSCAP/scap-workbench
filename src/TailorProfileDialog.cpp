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

const QString TailorProfileDialog::XCCDF11ProfileIDRegExp("[a-zA-Z0-9\\-_.]+");

// Regex from XCCDF 1.2 official XSD "xccdf_[^_]+_profile_.+"
// is unfortunately too permissive.
//
// The spec calls for xccdf_N_profile_S where N is reverse DNS-style address
// and S is NCName.
//
// We are more strict than the spec but it keeps the regex simple and the
// restrictions imposed aren't severe.

const QString TailorProfileDialog::XCCDF12ProfileIDRegExp("xccdf_[a-zA-Z0-9\\-.]+_profile_[a-zA-Z0-9\\-_.]+");

TailorProfileDialog::TailorProfileDialog(const QString& startId, bool xccdf12, QWidget* parent):
    QDialog(parent),
    mRegexp(xccdf12 ? XCCDF12ProfileIDRegExp : XCCDF11ProfileIDRegExp)
{
    mUI.setupUi(this);
    mUI.idLineEdit->setText(startId);
    onIdLineEditChanged(startId);

    mUI.xccdf11Warning->setVisible(!xccdf12);
    mUI.xccdf12Warning->setVisible(xccdf12);

    connect(mUI.idLineEdit, SIGNAL(textChanged(const QString&)), this, SLOT(onIdLineEditChanged(const QString&)));
}

TailorProfileDialog::~TailorProfileDialog()
{}

QString TailorProfileDialog::getProfileID() const
{
    return mUI.idLineEdit->text();
}

void TailorProfileDialog::onIdLineEditChanged(const QString& newText)
{
    mUI.buttonBox->button(QDialogButtonBox::Ok)->setEnabled(mRegexp.exactMatch(newText));
}
