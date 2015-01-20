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

/**
 * @brief Provides options such as package name, version, summary, etc... when saving SCAP as RPM
 *
 * Internally this uses the scap-as-rpm script shipped in openscap.
 *
 * @note Please use the SaveAsRPMDialog::saveSession static method where possible.
 */
class SaveAsRPMDialog : public QDialog
{
    Q_OBJECT

    private:
        explicit SaveAsRPMDialog(ScanningSession* session, MainWindow* parent);
        virtual ~SaveAsRPMDialog();

    public:
        /**
         * @brief Provides a dialog to the user to save given session
         *
         * @param session Session to save
         * @param parent Parent main window
         */
        static void saveSession(ScanningSession* session, MainWindow* parent);

    private slots:
        void slotFinished(int result);

    private:
        MainWindow* mMainWindow;
        Ui_SaveAsRPMDialog mUI;

        ScanningSession* mScanningSession;
};

#endif
