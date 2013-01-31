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

#include "ForwardDecls.h"

#include <QMainWindow>
#include <QThread>

extern "C"
{
#include <xccdf_benchmark.h>
}

#include "ui_MainWindow.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

    public:
        explicit MainWindow(QWidget* parent = 0);
        virtual ~MainWindow();

    public slots:
        void clearResults();
        void openFile(const QString& path);
        void closeFile();
        void openFileDialog();

        void scanAsync();
        void cancelScanAsync();

    private:
        void reloadSession();
        void refreshProfiles();
        void cleanupScanThread();

        Ui_MainWindow mUI;
        struct xccdf_session* mSession;

        QThread* mScanThread;
        Evaluator* mEvaluator;

    signals:
        void cancelScan();

    private slots:
        void checklistComboboxChanged(const QString& text);
        void profileComboboxChanged(int index);

        void scanProgressReport(const QString& rule_id, const QString& result);
        void scanCanceled();
        void scanFinished();
};
