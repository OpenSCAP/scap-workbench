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

#ifndef SCAP_WORKBENCH_RESULT_VIEWER_H_
#define SCAP_WORKBENCH_RESULT_VIEWER_H_

#include "ForwardDecls.h"

#include <QWidget>
#include <QTemporaryFile>
#include <QUrl>
#include <QMenu>
#include <QLabel>

extern "C"
{
#include <xccdf_benchmark.h>
}

#include "ui_ResultViewer.h"

/**
 * @brief Handles all result and report viewing/saving
 *
 * This is a final class and is not supposed to be inherited.
 */
class ResultViewer : public QWidget
{
    Q_OBJECT

    public:
        explicit ResultViewer(QWidget* parent = 0);
        virtual ~ResultViewer();

        /**
         * @brief Clears all kept content
         */
        void clear();

        /**
         * @brief Loads and keeps results and report in given scanner
         */
        void loadContent(Scanner* scanner);

        /**
         * @brief Retrieve currently loaded ARF
         *
         * This can be used to perform offline remediation for example.
         */
        const QByteArray& getARF() const;

    private slots:
        /// Pops up a save dialog for HTML report
        void saveReport();
        /// Opens the HTML report using Qt desktop services
        void openReport();
        /// Pops up a save dialog for XCCDF result file
        void saveResults();
        /// Pops up a save dialog for ARF / result datastream
        void saveARF();

    private:
        Ui_ResultViewer mUI;

        QAction* mSaveResultsAction;
        QAction* mSaveARFAction;
        QAction* mSaveReportAction;
        QMenu* mSaveMenu;

        QString mInputBaseName;

        QByteArray mResults;
        QByteArray mReport;
        /// If user requests to open the file via desktop services
        QTemporaryFile* mReportFile;
        QByteArray mARF;
};

#endif
