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
 * @brief Messages are divided into categories.
 *
 * Info is not important and does not make the DiagnosticDialog pop up.
 * All the other categories cause the dialog to be shown.
 *
 * This enum is not used directly but only internally. You are advised
 * to use the {info,warning,exception,error}Message methods.
 */
enum MessageSeverity
{
    MS_INFO,
    MS_WARNING,
    MS_EXCEPTION,
    MS_ERROR
};

/**
 * @brief MessageFormat can be any subset of this flags
 */
enum MessageFormat
{
    MF_STANDARD = 0x01,
    MF_PREFORMATTED = 0x02, // Preserve whitespaces to output
    MF_XML = 0x04, // Replace xml metacharacters with xml entities
    MF_PREFORMATTED_XML = MF_PREFORMATTED | MF_XML,
};

/**
 * @brief Workbench displays errors and warnings, this dialog groups them
 *
 * This is a final class and is not supposed to be inherited.
 */
class DiagnosticsDialog : public QDialog
{
    Q_OBJECT

    public:
        explicit DiagnosticsDialog(QWidget* parent = 0);
        virtual ~DiagnosticsDialog();

        /**
         * @brief Clears all kept content
         */
        void clear();

        /**
         * @brief Blocks execution until user hides this dialog
         *
         * @param interval Polling interval in msec
         */
        void waitUntilHidden(unsigned int interval = 100);

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
        void infoMessage(const QString& message, MessageFormat format = MF_STANDARD);

        /**
         * @brief Scanner triggers this to show a warning message
         *
         * A warning message will open the diagnostics dialog if it isn't
         * being shown already.
         */
        void warningMessage(const QString& message, MessageFormat format = MF_STANDARD);

        /**
         * @brief Scanner triggers this to show an error message
         *
         * An error message will open the diagnostics dialog if it isn't
         * being shown already.
         */
        void errorMessage(const QString& message, MessageFormat format = MF_STANDARD);

        /**
         * @brief Report a caught exception.
         */
        void exceptionMessage(const std::exception& e, const QString& context = "", MessageFormat format = MF_STANDARD);

    private:
        void pushMessage(MessageSeverity severity, const QString& fullMessage, MessageFormat format = MF_STANDARD);

        /**
         * @brief Pushes a single info message containing version info
         */
        void dumpVersionInfo();

        Ui_DiagnosticsDialog mUI;

    private slots:
        /**
         * @brief Copies plain text log to system clipboard, useful for bug reports
         */
        void copyToClipboard();
};

#endif
