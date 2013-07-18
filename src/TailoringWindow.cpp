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

#include "TailoringWindow.h"
#include <set>

XCCDFItemPropertiesDockWidget::XCCDFItemPropertiesDockWidget(QWidget* parent):
    QDockWidget(parent),

    mXccdfItem(0)
{
    mUI.setupUi(this);

    refresh();
}

XCCDFItemPropertiesDockWidget::~XCCDFItemPropertiesDockWidget()
{}

void XCCDFItemPropertiesDockWidget::setXccdfItem(struct xccdf_item* item)
{
    mXccdfItem = item;

    refresh();
}

void XCCDFItemPropertiesDockWidget::refresh()
{
    if (mXccdfItem)
    {
        struct oscap_text_iterator* title = xccdf_item_get_title(mXccdfItem);
        char* titleText = oscap_textlist_get_preferred_plaintext(title, NULL);
        mUI.titleLineEdit->setText(QString(titleText));
        free(titleText);

        mUI.idLineEdit->setText(QString(xccdf_item_get_id(mXccdfItem)));
    }
    else
    {
        mUI.titleLineEdit->setText("<no item selected>");
        mUI.idLineEdit->setText("");
    }
}

TailoringWindow::TailoringWindow(struct xccdf_profile* profile, QWidget* parent):
    QMainWindow(parent),
    mItemPropertiesDockWidget(new XCCDFItemPropertiesDockWidget(this)),

    mProfile(profile)
{
    mUI.setupUi(this);
    addDockWidget(Qt::RightDockWidgetArea, mItemPropertiesDockWidget);

    QObject::connect(
        mUI.itemsTree, SIGNAL(currentItemChanged(QTreeWidgetItem*, QTreeWidgetItem*)),
        this, SLOT(currentXccdfItemChanged(QTreeWidgetItem*, QTreeWidgetItem*))
    );

    struct xccdf_benchmark* benchmark = xccdf_item_get_benchmark(xccdf_profile_to_item(profile));
    QTreeWidgetItem* benchmarkItem = new QTreeWidgetItem();
    // benchmark can't be unselected
    benchmarkItem->setFlags(
        Qt::ItemIsSelectable |
        /*Qt::ItemIsUserCheckable |*/
        Qt::ItemIsEnabled);
    mUI.itemsTree->addTopLevelItem(benchmarkItem);

    synchronizeTreeItem(benchmarkItem, xccdf_benchmark_to_item(benchmark));

    show();
}

TailoringWindow::~TailoringWindow()
{}

inline struct xccdf_item* getXccdfItemFromTreeItem(QTreeWidgetItem* treeItem)
{
    QVariant xccdfItem = treeItem->data(0, Qt::UserRole);
    return reinterpret_cast<struct xccdf_item*>(xccdfItem.value<void*>());
}

void TailoringWindow::synchronizeTreeItem(QTreeWidgetItem* treeItem, struct xccdf_item* xccdfItem)
{
    //if (treeItem == NULL || xccdfItem == NULL)
    //    return;

    struct oscap_text_iterator* title = xccdf_item_get_title(xccdfItem);
    char* titleText = oscap_textlist_get_preferred_plaintext(title, NULL);
    treeItem->setText(0, QString(titleText));
    free(titleText);

    const unsigned int typeColumn = 1;

    switch (xccdf_item_get_type(xccdfItem))
    {
        case XCCDF_BENCHMARK:
            treeItem->setText(typeColumn, QString("Benchmark"));
            break;

        case XCCDF_GROUP:
            treeItem->setText(typeColumn, QString("Group"));
            break;

        case XCCDF_RULE:
            treeItem->setText(typeColumn, QString("Rule"));
            break;

        default:
            treeItem->setText(typeColumn, QString("Unknown"));
            break;
    }

    treeItem->setText(2, QString(xccdf_item_get_id(xccdfItem)));
    treeItem->setData(0, Qt::UserRole, QVariant::fromValue(reinterpret_cast<void*>(xccdfItem)));

    std::set<struct xccdf_item*> itemsToAdd;
    struct xccdf_item_iterator* itemsIt = NULL;

    switch (xccdf_item_get_type(xccdfItem))
    {
        case XCCDF_GROUP:
            itemsIt = xccdf_group_get_content(xccdf_item_to_group(xccdfItem));
            break;
        case XCCDF_BENCHMARK:
            itemsIt = xccdf_benchmark_get_content(xccdf_item_to_benchmark(xccdfItem));
            break;
        default:
            break;
    }

    if (itemsIt != NULL)
    {
        while (xccdf_item_iterator_has_more(itemsIt))
        {
            struct xccdf_item* childItem = xccdf_item_iterator_next(itemsIt);
            itemsToAdd.insert(childItem);
        }
        xccdf_item_iterator_free(itemsIt);
    }

    std::set<QTreeWidgetItem*> treeItemsToRemove;
    for (int i = 0; i < treeItem->childCount(); ++i)
    {
        QTreeWidgetItem* childTreeItem = treeItem->child(i);
        struct xccdf_item* childXccdfItem = getXccdfItemFromTreeItem(childTreeItem);

        if (itemsToAdd.find(childXccdfItem) == itemsToAdd.end())
        {
            treeItemsToRemove.insert(childTreeItem);
        }
        else
        {
            synchronizeTreeItem(childTreeItem, childXccdfItem);
            itemsToAdd.erase(childXccdfItem);
        }
    }

    for (std::set<QTreeWidgetItem*>::const_iterator it = treeItemsToRemove.begin();
         it != treeItemsToRemove.end(); ++it)
    {
        // this will remove it from the tree as well, see ~QTreeWidgetItem()
        delete *it;
    }

    for (std::set<struct xccdf_item*>::const_iterator it = itemsToAdd.begin();
         it != itemsToAdd.end(); ++it)
    {
        QTreeWidgetItem* childTreeItem = new QTreeWidgetItem();
        childTreeItem->setFlags(
            Qt::ItemIsSelectable |
            Qt::ItemIsUserCheckable |
            Qt::ItemIsEnabled);
        childTreeItem->setCheckState(0, Qt::Checked);

        treeItem->addChild(childTreeItem);
        struct xccdf_item* childXccdfItem = *it;

        synchronizeTreeItem(childTreeItem, childXccdfItem);
    }
}

void TailoringWindow::currentXccdfItemChanged(QTreeWidgetItem* current, QTreeWidgetItem* previous)
{
    struct xccdf_item* item = getXccdfItemFromTreeItem(current);
    mItemPropertiesDockWidget->setXccdfItem(item);
}
