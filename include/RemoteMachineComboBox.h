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

#ifndef SCAP_WORKBENCH_REMOTE_MACHINE_COMBOBOX_H_
#define SCAP_WORKBENCH_REMOTE_MACHINE_COMBOBOX_H_

#include "ForwardDecls.h"

#include <QWidget>
#include <QMenu>
#include <QStringList>
#include <QSettings>
#include <QComboBox>

#include "ui_RemoteMachineComboBox.h"

class RemoteMachineComboBox : public QWidget
{
    Q_OBJECT

    public:
        explicit RemoteMachineComboBox(QWidget* parent = 0);
        virtual ~RemoteMachineComboBox();

        QString getTarget() const;

        void setRecentMachineCount(unsigned int count);
        unsigned int getRecentMachineCount() const;

    public slots:
        void notifyTargetUsed(const QString& target);
        void clearHistory();

    protected slots:
        void updateHostPort(int index);

    private:
        void syncFromQSettings();
        void syncToQSettings();

        void syncRecentMenu();

        /// UI designed in Qt Designer
        Ui_RemoteMachineComboBox mUI;

        QSettings* mQSettings;

        QStringList mRecentTargets;
        QComboBox *mRecentComboBox;
};

#endif
