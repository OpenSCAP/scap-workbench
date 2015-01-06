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
#include "TailoringDockWidgets.h"
#include "TailoringUndoCommands.h"

#include "Exceptions.h"
#include "MainWindow.h"
#include "APIHelpers.h"
#include "Utils.h"

#include <QCryptographicHash>
#include <QMessageBox>
#include <QCloseEvent>
#include <QDesktopWidget>
#include <QUndoView>

#include <algorithm>
#include <cassert>

struct xccdf_item* TailoringWindow::getXccdfItemFromTreeItem(QTreeWidgetItem* treeItem)
{
    QVariant xccdfItem = treeItem->data(0, Qt::UserRole);
    return reinterpret_cast<struct xccdf_item*>(xccdfItem.value<void*>());
}

/**
 * This only handles changes in selection of just one tree item!
 */
void _syncXCCDFItemChildrenDisabledState(QTreeWidgetItem* treeItem, bool enabled)
{
    for (int i = 0; i < treeItem->childCount(); ++i)
    {
        QTreeWidgetItem* childTreeItem = treeItem->child(i);
        const bool childEnabled = !childTreeItem->isDisabled();

        if (!enabled && childEnabled)
        {
            childTreeItem->setDisabled(true);
            _syncXCCDFItemChildrenDisabledState(childTreeItem, false);
        }
        else if (enabled && !childEnabled)
        {
            childTreeItem->setDisabled(false);
            _syncXCCDFItemChildrenDisabledState(childTreeItem, true);
        }
    }
}

void _refreshXCCDFItemChildrenDisabledState(QTreeWidgetItem* treeItem, bool allAncestorsSelected)
{
    bool itemSelected = !(treeItem->flags() & Qt::ItemIsUserCheckable) || treeItem->checkState(0) == Qt::Checked;
    allAncestorsSelected = allAncestorsSelected && itemSelected;

    for (int i = 0; i < treeItem->childCount(); ++i)
    {
        QTreeWidgetItem* childTreeItem = treeItem->child(i);
        childTreeItem->setDisabled(!allAncestorsSelected);

        _refreshXCCDFItemChildrenDisabledState(childTreeItem, allAncestorsSelected);
    }
}

TailoringWindow::TailoringWindow(struct xccdf_policy* policy, struct xccdf_benchmark* benchmark, bool newProfile, MainWindow* parent):
    QMainWindow(parent),

    mParentMainWindow(parent),
    mQSettings(new QSettings(this)),

    mSynchronizeItemLock(0),

    mItemPropertiesDockWidget(new XCCDFItemPropertiesDockWidget(this)),
    mProfilePropertiesDockWidget(new ProfilePropertiesDockWidget(this, this)),
    mUndoViewDockWidget(new QDockWidget(this)),

    mSearchBox(new QLineEdit()),
    mSearchButton(new QPushButton("Search")),

    mPolicy(policy),
    mProfile(xccdf_policy_get_profile(policy)),
    mBenchmark(benchmark),

    mUndoStack(this),

    mNewProfile(newProfile),
    mChangesConfirmed(false),

    mSearchSkippedItems(0),
    mSearchCurrentNeedle("")
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
        mUI.confirmButton, SIGNAL(released()),
        this, SLOT(confirmAndClose())
    );

    QObject::connect(
        mUI.cancelButton, SIGNAL(released()),
        this, SLOT(close())
    );

    QObject::connect(
        mUI.deleteProfileButton, SIGNAL(released()),
        this, SLOT(deleteProfileAndDiscard())
    );

    addDockWidget(Qt::RightDockWidgetArea, mItemPropertiesDockWidget);
    addDockWidget(Qt::RightDockWidgetArea, mProfilePropertiesDockWidget);

    {
        QAction* undoAction = mUndoStack.createUndoAction(this, QObject::tr("Undo"));
        undoAction->setIcon(getShareIcon("edit-undo.png"));
        QAction* redoAction = mUndoStack.createRedoAction(this, QObject::tr("Redo"));
        redoAction->setIcon(getShareIcon("edit-redo.png"));

        mUI.toolBar->addAction(undoAction);
        mUI.toolBar->addAction(redoAction);
    }

    // Column 1 is for search keywords
    mUI.itemsTree->setColumnHidden(1, true);

    QObject::connect(
        mUI.itemsTree, SIGNAL(currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)),
        this, SLOT(itemSelectionChanged(QTreeWidgetItem*,QTreeWidgetItem*))
    );
    QObject::connect(
        mUI.itemsTree, SIGNAL(itemChanged(QTreeWidgetItem*,int)),
        this, SLOT(itemChanged(QTreeWidgetItem*,int))
    );
    QObject::connect(
        mUI.itemsTree, SIGNAL(itemExpanded(QTreeWidgetItem*)),
        this, SLOT(itemExpanded(QTreeWidgetItem*))
    );
    QObject::connect(
        mUI.itemsTree, SIGNAL(itemCollapsed(QTreeWidgetItem*)),
        this, SLOT(itemCollapsed(QTreeWidgetItem*))
    );

    QTreeWidgetItem* benchmarkItem = new QTreeWidgetItem();
    // benchmark can't be unselected
    benchmarkItem->setFlags(
        Qt::ItemIsSelectable |
        /*Qt::ItemIsUserCheckable |*/
        Qt::ItemIsEnabled);
    mUI.itemsTree->addTopLevelItem(benchmarkItem);

    synchronizeTreeItem(benchmarkItem, xccdf_benchmark_to_item(mBenchmark), true);
    _refreshXCCDFItemChildrenDisabledState(benchmarkItem, true);

    mUI.itemsTree->header()->setResizeMode(0, QHeaderView::ResizeToContents);
    mUI.itemsTree->header()->setStretchLastSection(false);

    deserializeCollapsedItems();
    syncCollapsedItems();

    setWindowTitle(QObject::tr("Tailoring \"%1\"").arg(oscapTextIteratorGetPreferred(xccdf_profile_get_title(mProfile))));

    mItemPropertiesDockWidget->refresh();
    mProfilePropertiesDockWidget->refresh();

    {
        mUndoViewDockWidget->setWindowTitle(QObject::tr("Undo History"));
        mUndoViewDockWidget->setWidget(new QUndoView(&mUndoStack, mUndoViewDockWidget));
        addDockWidget(Qt::RightDockWidgetArea, mUndoViewDockWidget);
        mUndoViewDockWidget->hide();

        mUI.toolBar->addAction(mUndoViewDockWidget->toggleViewAction());
    }

    mUI.toolBar->addSeparator();

    {
        QAction* action = new QAction(this);
        action->setText(QObject::tr("Deselect All"));

        QObject::connect(
            action, SIGNAL(triggered()),
            this, SLOT(deselectAllChildrenItems())
        );

        mUI.toolBar->addAction(action);
    }

    mUI.toolBar->addSeparator();

    QAction* searchBoxFocusAction = new QAction(QObject::tr("Search"), this);
    searchBoxFocusAction->setShortcut(QKeySequence::Find);
    addAction(searchBoxFocusAction);

    QObject::connect(
        searchBoxFocusAction, SIGNAL(triggered()),
        mSearchBox, SLOT(setFocus())
    );

    mSearchBox->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Preferred);
    mUI.toolBar->addSeparator();
    mUI.toolBar->addWidget(mSearchBox);

    mSearchButton->setShortcut(QKeySequence::FindNext);

    mUI.toolBar->addWidget(mSearchButton);

    QObject::connect(
        mSearchBox, SIGNAL(editingFinished()),
        this, SLOT(searchNext())
    );

    QObject::connect(
        mSearchButton, SIGNAL(released()),
        this, SLOT(searchNext())
    );

    // start centered
    move(QApplication::desktop()->screen()->rect().center() - rect().center());
    show();
}

TailoringWindow::~TailoringWindow()
{
    delete mQSettings;
}

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

    const QString title = oscapTextIteratorGetPreferred(xccdf_item_get_title(xccdfItem));
    treeItem->setText(0, title);

    QString searchable = QString("%1 %2").arg(title, QString::fromUtf8(xccdf_item_get_id(xccdfItem)));
    switch (xccdf_item_get_type(xccdfItem))
    {
        case XCCDF_BENCHMARK:
            treeItem->setIcon(0, getShareIcon("benchmark.png"));
            break;

        case XCCDF_GROUP:
            treeItem->setIcon(0, getShareIcon("group.png"));
            break;

        case XCCDF_RULE:
            treeItem->setIcon(0, getShareIcon("rule.png"));
            {
                struct xccdf_ident_iterator* idents = xccdf_rule_get_idents(xccdf_item_to_rule(xccdfItem));
                while (xccdf_ident_iterator_has_more(idents))
                {
                    struct xccdf_ident* ident = xccdf_ident_iterator_next(idents);
                    searchable += ' ';
                    searchable += QString::fromUtf8(xccdf_ident_get_id(ident));
                }
                xccdf_ident_iterator_free(idents);
            }
            break;

        case XCCDF_VALUE:
            treeItem->setIcon(0, getShareIcon("value.png"));
            break;

        default:
            treeItem->setIcon(0, QIcon());
            break;
    }

    treeItem->setText(1, searchable);

    treeItem->setData(0, Qt::UserRole, QVariant::fromValue(reinterpret_cast<void*>(xccdfItem)));

    xccdf_type_t xccdfItemType = xccdf_item_get_type(xccdfItem);
    switch (xccdfItemType)
    {
        case XCCDF_RULE:
        case XCCDF_GROUP:
        {
            treeItem->setFlags(treeItem->flags() | Qt::ItemIsUserCheckable);
            treeItem->setCheckState(0,
                    getXccdfItemInternalSelected(mPolicy, xccdfItem) ? Qt::Checked : Qt::Unchecked);
            _syncXCCDFItemChildrenDisabledState(treeItem, treeItem->checkState(0));
            break;
        }
        case XCCDF_VALUE:
            treeItem->setFlags(treeItem->flags() & ~Qt::ItemIsUserCheckable);
        default:
            break;
    }

    if (recursive)
    {
        typedef std::vector<struct xccdf_item*> XCCDFItemVector;
        typedef std::map<struct xccdf_item*, QTreeWidgetItem*> XCCDFToQtItemMap;

        XCCDFItemVector itemsToAdd;
        XCCDFToQtItemMap existingItemsMap;

        // valuesIt contains Values
        struct xccdf_value_iterator* valuesIt = NULL;
        // itemsIt contains Rules and Groups
        struct xccdf_item_iterator* itemsIt = NULL;

        switch (xccdfItemType)
        {
            case XCCDF_GROUP:
                valuesIt = xccdf_group_get_values(xccdf_item_to_group(xccdfItem));
                itemsIt = xccdf_group_get_content(xccdf_item_to_group(xccdfItem));
                break;
            case XCCDF_BENCHMARK:
                valuesIt = xccdf_benchmark_get_values(xccdf_item_to_benchmark(xccdfItem));
                itemsIt = xccdf_benchmark_get_content(xccdf_item_to_benchmark(xccdfItem));
                break;
            default:
                break;
        }

        if (valuesIt != NULL)
        {
            while (xccdf_value_iterator_has_more(valuesIt))
            {
                struct xccdf_value* childItem = xccdf_value_iterator_next(valuesIt);
                itemsToAdd.push_back(xccdf_value_to_item(childItem));
            }
            xccdf_value_iterator_free(valuesIt);
        }

        if (itemsIt != NULL)
        {
            while (xccdf_item_iterator_has_more(itemsIt))
            {
                struct xccdf_item* childItem = xccdf_item_iterator_next(itemsIt);
                itemsToAdd.push_back(childItem);
            }
            xccdf_item_iterator_free(itemsIt);
        }

        for (int i = 0; i < treeItem->childCount(); ++i)
        {
            QTreeWidgetItem* childTreeItem = treeItem->child(i);
            struct xccdf_item* childXccdfItem = getXccdfItemFromTreeItem(childTreeItem);

            if (std::find(itemsToAdd.begin(), itemsToAdd.end(), childXccdfItem) == itemsToAdd.end())
            {
                // this will remove it from the tree as well, see ~QTreeWidgetItem()
                delete childTreeItem;
            }
            else
            {
                existingItemsMap[childXccdfItem] = childTreeItem;
            }
        }

        unsigned int idx = 0;
        for (XCCDFItemVector::const_iterator it = itemsToAdd.begin();
                it != itemsToAdd.end(); ++it, ++idx)
        {
            struct xccdf_item* childXccdfItem = *it;
            QTreeWidgetItem* childTreeItem = 0;

            XCCDFToQtItemMap::iterator mapIt = existingItemsMap.find(childXccdfItem);

            if (mapIt == existingItemsMap.end())
            {
                childTreeItem = new QTreeWidgetItem();

                childTreeItem->setFlags(
                        Qt::ItemIsSelectable |
                        Qt::ItemIsEnabled);

                treeItem->insertChild(idx, childTreeItem);
            }
            else
            {
                childTreeItem = mapIt->second;
            }

            synchronizeTreeItem(childTreeItem, childXccdfItem, true);
        }
    }

    --mSynchronizeItemLock;
}

void TailoringWindow::setValueValue(struct xccdf_value* xccdfValue, const QString& newValue)
{
    struct xccdf_setvalue* setvalue = xccdf_setvalue_new();
    xccdf_setvalue_set_item(setvalue, xccdf_value_get_id(xccdfValue));
    xccdf_setvalue_set_value(setvalue, newValue.toUtf8().constData());

    xccdf_profile_add_setvalue(mProfile, setvalue);

    assert(getCurrentValueValue(xccdfValue) == newValue);
}

void TailoringWindow::refreshXccdfItemPropertiesDockWidget()
{
    mItemPropertiesDockWidget->refresh();
}

QString TailoringWindow::getCurrentValueValue(struct xccdf_value* xccdfValue)
{
    return QString::fromUtf8(xccdf_policy_get_value_of_item(mPolicy, xccdf_value_to_item(xccdfValue)));
}

void TailoringWindow::setValueValueWithUndoCommand(struct xccdf_value* xccdfValue, const QString& newValue)
{
    mUndoStack.push(new XCCDFValueChangeUndoCommand(this, xccdfValue, newValue, getCurrentValueValue(xccdfValue)));
}

void TailoringWindow::deselectAllChildrenItems(QTreeWidgetItem* parent, bool undoMacro)
{
    if (parent == 0)
        parent = mUI.itemsTree->topLevelItem(0);

    if (undoMacro)
        mUndoStack.beginMacro("Deselect All");

    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(parent);
    switch (xccdf_item_get_type(xccdfItem))
    {
        case XCCDF_BENCHMARK:
        case XCCDF_GROUP:
            for (int i = 0; i < parent->childCount(); ++i)
                deselectAllChildrenItems(parent->child(i), false);
            break;

        case XCCDF_RULE:
            parent->setCheckState(0, Qt::Unchecked);
            break;

        default:
            break;
    }

    if (undoMacro)
        mUndoStack.endMacro();
}

QString TailoringWindow::getProfileID() const
{
    return QString::fromUtf8(xccdf_profile_get_id(mProfile));
}

void TailoringWindow::setProfileTitle(const QString& title)
{
    struct oscap_text_iterator* titles = xccdf_profile_get_title(mProfile);
    struct oscap_text* titleText = 0;
    while (oscap_text_iterator_has_more(titles))
    {
        struct oscap_text* titleCandidate = oscap_text_iterator_next(titles);
        if (!titleText || strcmp(oscap_text_get_lang(titleCandidate), OSCAP_LANG_DEFAULT) == 0)
            titleText = titleCandidate;
    }
    oscap_text_iterator_free(titles);

    if (titleText)
    {
        oscap_text_set_text(titleText, title.toUtf8().constData());
        oscap_text_set_lang(titleText, OSCAP_LANG_DEFAULT);
    }
    else
    {
        // FIXME: we cannot add new title using this API :-(
        throw TailoringWindowException("Not suitable oscap_text found that we could edit to change profile title.");
    }

    assert(getProfileTitle() == title);
}

QString TailoringWindow::getProfileTitle() const
{
    return oscapTextIteratorGetPreferred(xccdf_profile_get_title(mProfile));
}

void TailoringWindow::setProfileTitleWithUndoCommand(const QString& newTitle)
{
    mUndoStack.push(new ProfileTitleChangeUndoCommand(this, getProfileTitle(), newTitle));
}

void TailoringWindow::setProfileDescription(const QString& description)
{
    struct oscap_text_iterator* descriptions = xccdf_profile_get_description(mProfile);
    struct oscap_text* descText = 0;
    while (oscap_text_iterator_has_more(descriptions))
    {
        struct oscap_text* descCandidate = oscap_text_iterator_next(descriptions);
        if (!descText || strcmp(oscap_text_get_lang(descCandidate), OSCAP_LANG_DEFAULT) == 0)
            descText = descCandidate;
    }
    oscap_text_iterator_free(descriptions);

    if (descText)
    {
        oscap_text_set_text(descText, description.toUtf8().constData());
        oscap_text_set_lang(descText, OSCAP_LANG_DEFAULT);
    }
    else
    {
        // FIXME: we cannot add new title using this API :-(
        throw TailoringWindowException("Not suitable oscap_text found that we could edit to change profile description.");
    }

    assert(getProfileDescription() == description);
}

QString TailoringWindow::getProfileDescription() const
{
    return oscapTextIteratorGetPreferred(xccdf_profile_get_description(mProfile));
}

void TailoringWindow::setProfileDescriptionWithUndoCommand(const QString& newDescription)
{
    mUndoStack.push(new ProfileDescriptionChangeUndoCommand(this, getProfileDescription(), newDescription));
}

QString TailoringWindow::getXCCDFItemTitle(struct xccdf_item* item) const
{
    return oscapItemGetReadableTitle(item, mPolicy);
}

QString TailoringWindow::getXCCDFItemDescription(struct xccdf_item* item) const
{
    return oscapItemGetReadableDescription(item, mPolicy);
}

void TailoringWindow::refreshProfileDockWidget()
{
    mProfilePropertiesDockWidget->refresh();
}

void TailoringWindow::confirmAndClose()
{
    mChangesConfirmed = true;

    close();
}

void TailoringWindow::deleteProfileAndDiscard()
{
    mChangesConfirmed = false;
    mNewProfile = true;

    close();
}

void TailoringWindow::closeEvent(QCloseEvent * event)
{
    if (!mChangesConfirmed)
    {
        if (QMessageBox::question(this, QObject::tr("Discard changes?"),
            QObject::tr("Are you sure you want to discard all changes performed in this tailoring window?"),
            QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::No)
        {
            event->ignore();
            return;
        }

        // undo everything
        mUndoStack.setIndex(0);
        // TODO: Delete the profile if it was created as a tailoring action
    }

    serializeCollapsedItems();

    QMainWindow::closeEvent(event);

    // TODO: This is the only place where we depend on MainWindow which really sucks
    //       and makes this code more spaghetti-fied. Ideally MainWindow would handle
    //       this connection but there are no signals for window closure, the only
    //       way to react is to reimplement closeEvent... This needs further research.

    if (mParentMainWindow)
    {
        mParentMainWindow->notifyTailoringFinished(mNewProfile, mChangesConfirmed);
    }
}

QString TailoringWindow::getQSettingsKey() const
{
    const QString filePath = mParentMainWindow->getOpenedFilePath();
    QCryptographicHash hash(QCryptographicHash::Sha1);
    hash.addData(filePath.toUtf8());
    return QString("collapsed_items_%1").arg(QString(hash.result().toHex()));
}

void TailoringWindow::deserializeCollapsedItems()
{
    const QStringList list = mQSettings->value(getQSettingsKey()).toStringList();
    mCollapsedItemIds = QSet<QString>::fromList(list);
}

void TailoringWindow::serializeCollapsedItems()
{
    if (mCollapsedItemIds.isEmpty())
        mQSettings->remove(getQSettingsKey());
    else
        mQSettings->setValue(getQSettingsKey(), QVariant(mCollapsedItemIds.toList()));
}

void TailoringWindow::syncCollapsedItems()
{
    QSet<QString> usedCollapsedItems;
    syncCollapsedItem(mUI.itemsTree->topLevelItem(0), usedCollapsedItems);
    // This "cleans" the ids of non-existent ones.
    // That's useful when the content changes and avoids cruft buildup in the settings files.
    mCollapsedItemIds = usedCollapsedItems;
}

void TailoringWindow::syncCollapsedItem(QTreeWidgetItem* item, QSet<QString>& usedCollapsedIds)
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(item);
    const QString id = QString::fromUtf8(xccdf_item_get_id(xccdfItem));

    if (mCollapsedItemIds.contains(id))
    {
        mUI.itemsTree->collapseItem(item);
        usedCollapsedIds.insert(id);
    }
    else
    {
        mUI.itemsTree->expandItem(item);
    }

    for (int i = 0; i < item->childCount(); ++i)
        syncCollapsedItem(item->child(i), usedCollapsedIds);
}

void TailoringWindow::searchNext()
{
    const QString& needle = mSearchBox->text();

    if (needle == mSearchCurrentNeedle)
        ++mSearchSkippedItems;
    else
        mSearchSkippedItems = 0;

    mSearchCurrentNeedle = needle;

    // FIXME: We could cache this when skipping to save CPU cycles but it's not worth
    //        as searching takes miliseconds even for huge XCCDF files.
    // Column 1 is used for search keywords
    QList<QTreeWidgetItem*> matches = mUI.itemsTree->findItems(mSearchCurrentNeedle, Qt::MatchContains | Qt::MatchRecursive, 1);
    if (matches.size() > 0)
    {
        mSearchSkippedItems = mSearchSkippedItems % matches.size(); // wrap around

        QTreeWidgetItem* match = matches.at(mSearchSkippedItems);
        mUI.itemsTree->setCurrentItem(match);

        mSearchBox->setStyleSheet("");
    }
    else
    {
        mSearchSkippedItems = 0;
        // In case of no match we intentionally do not change selection
        mSearchBox->setStyleSheet("background: #f66");
    }
}

void TailoringWindow::itemSelectionChanged(QTreeWidgetItem* current, QTreeWidgetItem* previous)
{
    struct xccdf_item* item = getXccdfItemFromTreeItem(current);
    mItemPropertiesDockWidget->setXccdfItem(item, mPolicy);
}

void TailoringWindow::itemChanged(QTreeWidgetItem* treeItem, int column)
{
    if (mSynchronizeItemLock > 0)
        return;

    const bool checkState = treeItem->checkState(0) == Qt::Checked;

    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(treeItem);
    if (!xccdfItem)
        return;

    if (xccdf_item_get_type(xccdfItem) == XCCDF_VALUE)
        return;

    const bool itemCheckState = getXccdfItemInternalSelected(mPolicy, xccdfItem);

    if (checkState != itemCheckState)
        mUndoStack.push(new XCCDFItemSelectUndoCommand(this, treeItem, checkState));

    _syncXCCDFItemChildrenDisabledState(treeItem, checkState);
}

void TailoringWindow::itemExpanded(QTreeWidgetItem* item)
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(item);
    const QString id = QString::fromUtf8(xccdf_item_get_id(xccdfItem));
    mCollapsedItemIds.remove(id);
}

void TailoringWindow::itemCollapsed(QTreeWidgetItem* item)
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(item);
    const QString id = QString::fromUtf8(xccdf_item_get_id(xccdfItem));
    mCollapsedItemIds.insert(id);
}
