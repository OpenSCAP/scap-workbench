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

#ifndef SCAP_WORKBENCH_DIAGNOSTICS_DIALOG_H_
#define SCAP_WORKBENCH_DIAGNOSTICS_DIALOG_H_

#include "ForwardDecls.h"

#include <QDialog>

extern "C"
{
#include <xccdf_benchmark.h>
}

#include "ui_DiagnosticsDialog.h"

/**
 * @brief Workbench displays errors and warnings, this dialog groups them
 *
 * This is a final class and is not supposed to be inherited.
 */
class DiagnosticsDialog : public QDialog
{
    Q_OBJECT

    public:
        DiagnosticsDialog(QWidget* parent = 0);
        virtual ~DiagnosticsDialog();

        /**
         * @brief Clears all kept content
         */
        void clear();

    public slots:
        /**
         * @brief Scanner triggers this to show a message about progress
         *
         * Example: Connecting to remote target..., Copying input file..., etc.
         * No action is required by the user upon receiving this message.
         *
         * The diagnostics dialog will not open when just these messages are
         * received.
         */
        void infoMessage(const QString& message);

        /**
         * @brief Scanner triggers this to show a warning message
         *
         * A warning message will open the diagnostics dialog if it isn't
         * being shown already.
         */
        void warningMessage(const QString& message);

        /**
         * @brief Scanner triggers this to show an error message
         *
         * An error message will open the diagnostics dialog if it isn't
         * being shown already.
         */
        void errorMessage(const QString& message);

    private:
        void pushMessage(const QString& fullMessage, const bool error = false);

        Ui_DiagnosticsDialog mUI;
};

#endif
