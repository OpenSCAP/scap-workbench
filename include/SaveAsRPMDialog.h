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

#ifndef SCAP_WORKBENCH_SAVE_AS_RPM_DIALOG_H_
#define SCAP_WORKBENCH_SAVE_AS_RPM_DIALOG_H_

#include "ForwardDecls.h"

#include <QDialog>
#include "ui_SaveAsRPMDialog.h"

class SaveAsRPMDialog : public QDialog
{
    Q_OBJECT

    public:
        SaveAsRPMDialog(ScanningSession* session, QWidget* parent = 0);
        virtual ~SaveAsRPMDialog();

    protected slots:
        void slotFinished(int result);

    private:
        Ui_SaveAsRPMDialog mUI;

        ScanningSession* mScanningSession;
};

#endif
