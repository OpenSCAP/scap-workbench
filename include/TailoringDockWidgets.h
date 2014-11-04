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

#ifndef SCAP_WORKBENCH_TAILORING_DOCK_WIDGETS_H_
#define SCAP_WORKBENCH_TAILORING_DOCK_WIDGETS_H_

#include "ForwardDecls.h"
#include <QDockWidget>

extern "C"
{
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
}

#include "ui_ProfilePropertiesDockWidget.h"
#include "ui_XCCDFItemPropertiesDockWidget.h"

/**
 * @brief Displays profile properties and allows editing of profile title
 */
class ProfilePropertiesDockWidget : public QDockWidget
{
    Q_OBJECT

    public:
        explicit ProfilePropertiesDockWidget(TailoringWindow* window, QWidget* parent = 0);
        virtual ~ProfilePropertiesDockWidget();

        /**
         * @brief Takes profile's current ID and title and sets both QLineEdit widgets accordingly
         */
        void refresh();

    protected slots:
        void profileTitleChanged(const QString& newTitle);
        void profileDescriptionChanged();

    protected:
        /// Prevents a redo command being created when actions are undone or redone
        bool mRefreshInProgress;

        /// UI designed in Qt Designer
        Ui_ProfilePropertiesDockWidget mUI;

        /// Owner TailoringWindow that provides profile for editing/viewing
        TailoringWindow* mWindow;
};

/**
 * @brief Provides reference about currently selected XCCDF item
 */
class XCCDFItemPropertiesDockWidget : public QDockWidget
{
    Q_OBJECT

    public:
        explicit XCCDFItemPropertiesDockWidget(TailoringWindow* window, QWidget* parent = 0);
        virtual ~XCCDFItemPropertiesDockWidget();

        /**
         * @brief Changes currently inspected XCCDF item
         *
         * @note This method automatically calls refresh to load new data
         */
        void setXccdfItem(struct xccdf_item* item, struct xccdf_policy* policy);

        /**
         * @brief Loads properties from currently set XCCDF items and sets widgets accordingly
         */
        void refresh();

    protected slots:
        void valueChanged(const QString& newValue);
        void selectValue(const QUrl& url);
        void selectRule(const QUrl& url);

    protected:
        /// UI designed in Qt Designer
        Ui_XCCDFItemPropertiesDockWidget mUI;

        /// Currently inspected XCCDF item
        struct xccdf_item* mXccdfItem;
        struct xccdf_policy* mXccdfPolicy;

        bool mRefreshInProgress;

        /// Owner TailoringWindow that provides title and description for items
        TailoringWindow* mWindow;
};

#endif
