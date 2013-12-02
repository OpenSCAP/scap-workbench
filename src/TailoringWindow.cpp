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
#include "Exceptions.h"
#include "MainWindow.h"

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
        mUI.titleLineEdit->setText(QString::fromUtf8(titleText));
        free(titleText);

        mUI.idLineEdit->setText(QString::fromUtf8(xccdf_item_get_id(mXccdfItem)));

        struct oscap_text_iterator* description = xccdf_item_get_description(mXccdfItem);
        char* descriptionText = oscap_textlist_get_preferred_plaintext(description, NULL);
        mUI.descriptionTextEdit->setHtml(QString::fromUtf8(descriptionText));
        free(descriptionText);
    }
    else
    {
        mUI.titleLineEdit->setText("<no item selected>");
        mUI.idLineEdit->setText("");
        mUI.descriptionTextEdit->setHtml("");
    }
}

inline struct xccdf_item* getXccdfItemFromTreeItem(QTreeWidgetItem* treeItem)
{
    QVariant xccdfItem = treeItem->data(0, Qt::UserRole);
    return reinterpret_cast<struct xccdf_item*>(xccdfItem.value<void*>());
}

XCCDFItemSelectUndoCommand::XCCDFItemSelectUndoCommand(TailoringWindow* window, QTreeWidgetItem* item, bool newSelect):
    mWindow(window),
    mTreeItem(item),
    mNewSelect(newSelect)
{}

XCCDFItemSelectUndoCommand::~XCCDFItemSelectUndoCommand()
{}

int XCCDFItemSelectUndoCommand::id() const
{
    return 1;
}

void XCCDFItemSelectUndoCommand::redo()
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(mTreeItem);
    mWindow->setItemSelected(xccdfItem, mNewSelect);
    mWindow->synchronizeTreeItem(mTreeItem, xccdfItem, false);
}

void XCCDFItemSelectUndoCommand::undo()
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(mTreeItem);
    mWindow->setItemSelected(xccdfItem, !mNewSelect);
    mWindow->synchronizeTreeItem(mTreeItem, xccdfItem, false);
}

TailoringWindow::TailoringWindow(struct xccdf_policy* policy, struct xccdf_benchmark* benchmark, MainWindow* parent):
    QMainWindow(parent),

    mParentMainWindow(parent),

    mSynchronizeItemLock(0),

    mItemPropertiesDockWidget(new XCCDFItemPropertiesDockWidget(this)),

    mPolicy(policy),
    mProfile(xccdf_policy_get_profile(policy)),
    mBenchmark(benchmark),

    mUndoStack(this)
{
    // sanity check
    if (!mPolicy)
        throw TailoringWindowException("TailoringWindow needs a proper policy "
            "being given. NULL was given instead!");

    if (!mProfile)
        throw TailoringWindowException("TailoringWindow was given a non-NULL "
            "policy but profile associated with it is NULL. Can't proceed!");

    if (!mBenchmark)
        throw TailoringWindowException("TailoringWindow was given a NULL "
            "benchmark. Can't proceed!");

    mUI.setupUi(this);

    QObject::connect(
        mUI.finishButton, SIGNAL(released()),
        this, SLOT(close())
    );

    addDockWidget(Qt::RightDockWidgetArea, mItemPropertiesDockWidget);

    {
        QAction* undoAction = mUndoStack.createUndoAction(this);
        QAction* redoAction = mUndoStack.createRedoAction(this);

        mUI.toolBar->addAction(undoAction);
        mUI.toolBar->addAction(redoAction);
    }

    QObject::connect(
        mUI.itemsTree, SIGNAL(currentItemChanged(QTreeWidgetItem*, QTreeWidgetItem*)),
        this, SLOT(itemSelectionChanged(QTreeWidgetItem*, QTreeWidgetItem*))
    );

    QObject::connect(
        mUI.itemsTree, SIGNAL(itemChanged(QTreeWidgetItem*, int)),
        this, SLOT(itemChanged(QTreeWidgetItem*, int))
    );

    QTreeWidgetItem* benchmarkItem = new QTreeWidgetItem();
    // benchmark can't be unselected
    benchmarkItem->setFlags(
        Qt::ItemIsSelectable |
        /*Qt::ItemIsUserCheckable |*/
        Qt::ItemIsEnabled);
    mUI.itemsTree->addTopLevelItem(benchmarkItem);

    synchronizeTreeItem(benchmarkItem, xccdf_benchmark_to_item(mBenchmark), true);

    char* profile_title = oscap_textlist_get_preferred_plaintext(xccdf_profile_get_title(mProfile), NULL);
    setWindowTitle(QString("Tailoring '%1'").arg(QString::fromUtf8(profile_title)));
    free(profile_title);

    show();
}

TailoringWindow::~TailoringWindow()
{}

inline bool getXccdfItemInternalSelected(struct xccdf_policy* policy, struct xccdf_item* item)
{
    struct xccdf_select* select = xccdf_policy_get_select_by_id(policy, xccdf_item_get_id(item));
    return select ? xccdf_select_get_selected(select) : xccdf_item_get_selected(item);
}

void TailoringWindow::setItemSelected(struct xccdf_item* xccdfItem, bool selected)
{
    struct xccdf_select* newSelect = xccdf_select_new();
    xccdf_select_set_item(newSelect, xccdf_item_get_id(xccdfItem));
    xccdf_select_set_selected(newSelect, selected);

    xccdf_profile_add_select(mProfile, newSelect);
    xccdf_policy_add_select(mPolicy, xccdf_select_clone(newSelect));

    if (getXccdfItemInternalSelected(mPolicy, xccdfItem) != selected)
        throw TailoringWindowException(
             QString(
                 "Even though xccdf_select was added to both profile and policy "
                 "to make '%1' selected=%2, it remains selected=%3."
             ).arg(QString::fromUtf8(xccdf_item_get_id(xccdfItem))).arg(selected).arg(!selected)
        );
}

void TailoringWindow::synchronizeTreeItem(QTreeWidgetItem* treeItem, struct xccdf_item* xccdfItem, bool recursive)
{
    ++mSynchronizeItemLock;

    struct oscap_text_iterator* title = xccdf_item_get_title(xccdfItem);
    char* titleText = oscap_textlist_get_preferred_plaintext(title, NULL);
    treeItem->setText(0, QString::fromUtf8(titleText));
    free(titleText);

    const unsigned int typeColumn = 1;

    switch (xccdf_item_get_type(xccdfItem))
    {
        case XCCDF_BENCHMARK:
            treeItem->setText(typeColumn, QString("Benchmark"));
            // benchmark is the root of the tree, it makes no sense to have it collapsed
            mUI.itemsTree->expandItem(treeItem);
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

    treeItem->setText(2, QString::fromUtf8(xccdf_item_get_id(xccdfItem)));
    treeItem->setData(0, Qt::UserRole, QVariant::fromValue(reinterpret_cast<void*>(xccdfItem)));

    xccdf_type_t xccdfItemType = xccdf_item_get_type(xccdfItem);
    switch (xccdfItemType)
    {
        case XCCDF_RULE:
        case XCCDF_GROUP:
            treeItem->setCheckState(0,
                    getXccdfItemInternalSelected(mPolicy, xccdfItem) ? Qt::Checked : Qt::Unchecked);
            break;
        default:
            break;
    }

    if (recursive)
    {
        std::set<struct xccdf_item*> itemsToAdd;
        struct xccdf_item_iterator* itemsIt = NULL;

        switch (xccdfItemType)
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
                synchronizeTreeItem(childTreeItem, childXccdfItem, true);
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

            synchronizeTreeItem(childTreeItem, childXccdfItem, true);
        }
    }

    --mSynchronizeItemLock;
}

void TailoringWindow::closeEvent(QCloseEvent * event)
{
    QMainWindow::closeEvent(event);

    // TODO: This is the only place where we depend on MainWindow which really sucks
    //       and makes this code more spaghetti-fied. Ideally MainWindow would handle
    //       this connection but there are no signals for window closure, the only
    //       way to react is to reimplement closeEvent... This needs further research.

    if (mParentMainWindow)
        mParentMainWindow->refreshSelectedRulesTree();
}

void TailoringWindow::itemSelectionChanged(QTreeWidgetItem* current, QTreeWidgetItem* previous)
{
    struct xccdf_item* item = getXccdfItemFromTreeItem(current);
    mItemPropertiesDockWidget->setXccdfItem(item);
}

void TailoringWindow::itemChanged(QTreeWidgetItem* treeItem, int column)
{
    if (mSynchronizeItemLock > 0)
        return;

    const bool checkState = treeItem->checkState(0);

    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(treeItem);
    if (!xccdfItem)
        return;

    const bool itemCheckState = getXccdfItemInternalSelected(mPolicy, xccdfItem);

    if (checkState != itemCheckState)
        mUndoStack.push(new XCCDFItemSelectUndoCommand(this, treeItem, checkState));
}
