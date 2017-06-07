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

#ifndef SCAP_WORKBENCH_TAILOR_PROFILE_DIALOG_H_
#define SCAP_WORKBENCH_TAILOR_PROFILE_DIALOG_H_

#include "ForwardDecls.h"
#include <QDialog>
#include <QPushButton>

#include "ui_TailorProfileDialog.h"

class TailorProfileDialog : public QDialog
{
    Q_OBJECT

    public:
        TailorProfileDialog(const QString &startId, bool xccdf12, QWidget* parent = 0);
        virtual ~TailorProfileDialog();

        QString getProfileID() const;

    private slots:
        void onIdLineEditChanged(const QString& newText);

    private:
        /// UI designed in Qt Designer
        Ui_TailorProfileDialog mUI;
        QRegExp mRegexp;

        static const QString XCCDF11ProfileIDRegExp;
        static const QString XCCDF12ProfileIDRegExp;
};

#endif
