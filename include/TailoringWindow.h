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

#ifndef SCAP_WORKBENCH_TAILORING_WINDOW_H_
#define SCAP_WORKBENCH_TAILORING_WINDOW_H_

#include "ForwardDecls.h"

#include <QDialog>

extern "C"
{
#include <xccdf_benchmark.h>
}

#include "ui_TailoringWindow.h"
#include "ui_XCCDFItemPropertiesDockWidget.h"

class XCCDFItemPropertiesDockWidget : public QDockWidget
{
    Q_OBJECT

    public:
        XCCDFItemPropertiesDockWidget(QWidget* parent = 0);
        virtual ~XCCDFItemPropertiesDockWidget();

        void setXccdfItem(struct xccdf_item* item);
        void refresh();

    protected:
        /// UI designed in Qt Designer
        Ui_XCCDFItemPropertiesDockWidget mUI;

        struct xccdf_item* mXccdfItem;
};

/**
 * @brief Tailors given profile by editing it directly
 *
 * If you want to inherit a profile and tailor that, create a new profile,
 * set up the inheritance and then pass the new profile to this class.
 */
class TailoringWindow : public QMainWindow
{
    Q_OBJECT

    public:
        TailoringWindow(struct xccdf_profile* profile, QWidget* parent = 0);
        virtual ~TailoringWindow();

    protected:
        void synchronizeTreeItem(QTreeWidgetItem* treeItem, struct xccdf_item* xccdfItem);

        /// UI designed in Qt Designer
        Ui_TailoringWindow mUI;

        XCCDFItemPropertiesDockWidget* mItemPropertiesDockWidget;

        struct xccdf_profile* mProfile;

    protected slots:
        void currentXccdfItemChanged(QTreeWidgetItem* current, QTreeWidgetItem* previous);
};

#endif
