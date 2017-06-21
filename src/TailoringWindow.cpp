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
#include <QTimer>
#include <QDateTime>
#include <QStack>

#include <algorithm>
#include <cassert>

struct xccdf_item* TailoringWindow::getXccdfItemFromTreeItem(QTreeWidgetItem* treeItem)
{
    QVariant xccdfItem = treeItem->data(0, Qt::UserRole);
    return reinterpret_cast<struct xccdf_item*>(xccdfItem.value<void*>());
}

TailoringWindow::TailoringWindow(struct xccdf_policy* policy, struct xccdf_benchmark* benchmark, bool newProfile, MainWindow* parent):
    QMainWindow(),

    mParentMainWindow(parent),
    mQSettings(parent->getQSettings()),

    mSynchronizeItemLock(0),

    mProfileItem(0),
    mBenchmarkItem(0),

    mItemPropertiesDockWidget(new XCCDFItemPropertiesDockWidget(this)),
    mProfilePropertiesDockWidget(new ProfilePropertiesDockWidget(this, this)),
    mUndoViewDockWidget(new QDockWidget(this)),

    mSearchBox(new QLineEdit()),
    mSearchButton(new QPushButton("Search")),
    mSearchFeedback(new QLabel("")),

    mPolicy(policy),
    mProfile(xccdf_policy_get_profile(policy)),
    mBenchmark(benchmark),

    mUndoStack(this),

    mNewProfile(newProfile),
    mChangesConfirmed(false),

    mSearchSkippedItems(0),
    mSearchCurrentNeedle(""),
    
    
    mDeselectAllAction(new QAction(this))
{
    generateValueAffectsRulesMap(xccdf_benchmark_to_item(benchmark));

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
        mUI.confirmButton, SIGNAL(clicked()),
        this, SLOT(confirmAndClose())
    );

    QObject::connect(
        mUI.cancelButton, SIGNAL(clicked()),
        this, SLOT(close())
    );

    QObject::connect(
        mUI.deleteProfileButton, SIGNAL(clicked()),
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
    QObject::connect(&mUndoStack, SIGNAL(indexChanged(int)), this, SLOT(synchronizeTreeItem()));

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

    mProfileItem = new QTreeWidgetItem();
    mUI.itemsTree->addTopLevelItem(mProfileItem);
    mProfileItem->setExpanded(true);

    synchronizeProfileItem();

    mBenchmarkItem = new QTreeWidgetItem(mProfileItem);
    // benchmark can't be unselected
    mBenchmarkItem->setFlags(
        Qt::ItemIsSelectable |
        /*Qt::ItemIsUserCheckable |*/
        Qt::ItemIsEnabled);

    createTreeItem(mBenchmarkItem, xccdf_benchmark_to_item(mBenchmark));
    synchronizeTreeItem();

    mUI.itemsTree->header()->setResizeMode(0, QHeaderView::ResizeToContents);
    mUI.itemsTree->header()->setStretchLastSection(false);

    deserializeCollapsedItems();
    syncCollapsedItems();

    setWindowTitle(QObject::tr("Customizing \"%1\"").arg(oscapTextIteratorGetPreferred(xccdf_profile_get_title(mProfile))));

    mItemPropertiesDockWidget->refresh();
    mItemPropertiesDockWidget->hide();
    mProfilePropertiesDockWidget->refresh();
    mProfilePropertiesDockWidget->hide();

    {
        mUndoViewDockWidget->setWindowTitle(QObject::tr("Undo History"));
        mUndoViewDockWidget->setWidget(new QUndoView(&mUndoStack, mUndoViewDockWidget));
        addDockWidget(Qt::RightDockWidgetArea, mUndoViewDockWidget);
        mUndoViewDockWidget->hide();

        mUI.toolBar->addAction(mUndoViewDockWidget->toggleViewAction());
    }

    mUI.toolBar->addSeparator();

    mDeselectAllAction->setText(QObject::tr("Deselect All"));
    QObject::connect(
        mDeselectAllAction, SIGNAL(triggered()),
        this, SLOT(deselectAllChildrenItems())
    );
    mUI.toolBar->addAction(mDeselectAllAction);

    mUI.toolBar->addSeparator();

    QAction* searchBoxFocusAction = new QAction(QObject::tr("Search"), this);
    searchBoxFocusAction->setShortcut(QKeySequence::Find);
    addAction(searchBoxFocusAction);

    QObject::connect(
        searchBoxFocusAction, SIGNAL(triggered()),
        mSearchBox, SLOT(setFocus())
    );

    mSearchBox->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Maximum);
    mUI.toolBar->addWidget(mSearchBox);

    mSearchButton->setShortcut(QKeySequence::FindNext);

    mUI.toolBar->addWidget(mSearchButton);
    mSearchFeedback->setMargin(5);
    mUI.toolBar->addWidget(mSearchFeedback);

    QObject::connect(
        mSearchBox, SIGNAL(returnPressed()),
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

void TailoringWindow::synchronizeProfileItem()
{
    mProfileItem->setText(0, oscapTextIteratorGetPreferred(xccdf_profile_get_title(mProfile)));
    mProfileItem->setIcon(0, getShareIcon("profile.png"));
}

void TailoringWindow::synchronizeTreeItem()
{
    // If QTreeWidget remains visible during the sync, it'll recalculate its geometry for each checked
    // row. Configuring "visible" as false seems to be the only way to avoid entering the "if" in
    // https://github.com/qt/qt/blob/4.8/src/gui/itemviews/qabstractitemview.cpp#L3190
    mUI.itemsTree->setVisible(false);
    synchronizeTreeItemSelections(mBenchmarkItem);
    mUI.itemsTree->setVisible(true);
    
    // Enables/disables "Deselect All action based on weather the top level rules/groups are checked"
    bool anySelected = false;
    for (int i = 0; i < mBenchmarkItem->childCount(); ++i)
    {
        anySelected |= mBenchmarkItem->child(i)->checkState(0) != Qt::Unchecked;
    }
    mDeselectAllAction->setEnabled(anySelected);
}

void TailoringWindow::synchronizeTreeItemSelections(QTreeWidgetItem* treeItem)
{
    ++mSynchronizeItemLock;

    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(treeItem);
    xccdf_type_t xccdfItemType = xccdf_item_get_type(xccdfItem);
    switch (xccdfItemType)
    {
        case XCCDF_BENCHMARK:
            for (int i = 0; i < treeItem->childCount(); ++i)
                synchronizeTreeItemSelections(treeItem->child(i));
            break;
        case XCCDF_GROUP:
        {
            int selectableChildren = 0;
            int checkedChildren = 0;
            int partiallyCheckedChildren = 0;
            for (int i = 0; i < treeItem->childCount(); ++i)
            {
                QTreeWidgetItem* child = treeItem->child(i);
                synchronizeTreeItemSelections(child);
                selectableChildren += child->flags() & Qt::ItemIsUserCheckable ? 1 : 0;
                checkedChildren += child->checkState(0) == Qt::Checked ? 1 : 0;
                partiallyCheckedChildren += child->checkState(0) == Qt::PartiallyChecked ? 1 : 0;
            }

            if (selectableChildren > 0)
            {
                bool groupCurrentState = getXccdfItemInternalSelected(mPolicy, xccdfItem);
                bool groupNewCheckState = (checkedChildren + partiallyCheckedChildren) > 0;
                if (groupCurrentState != groupNewCheckState)
                    setItemSelected(xccdfItem, groupNewCheckState);

                if (groupNewCheckState)
                {
                    if (selectableChildren > checkedChildren)
                        treeItem->setCheckState(0, Qt::PartiallyChecked);
                    else
                        treeItem->setCheckState(0, Qt::Checked);
                }
                else
                {
                    treeItem->setCheckState(0, Qt::Unchecked);
                }
                break;
            }
            //fall through
        }
        case XCCDF_RULE:
            treeItem->setCheckState(0,
                    getXccdfItemInternalSelected(mPolicy, xccdfItem) ? Qt::Checked : Qt::Unchecked);
            break;
        default:
            break;
    }

    --mSynchronizeItemLock;
}

void TailoringWindow::createSelectionMacro(QTreeWidgetItem* treeItem, bool checkState, const QString& commandName)
{
    mUndoStack.beginMacro(commandName);

    QStack<QTreeWidgetItem*> stack;
    stack.push(treeItem);
    while (!stack.isEmpty())
    {
        QTreeWidgetItem* curr = stack.pop();
        bool currCheckState = curr->checkState(0) == Qt::Checked;
        if ((curr->flags() & Qt::ItemIsUserCheckable) && (treeItem == curr || currCheckState != checkState))
        {
            mUndoStack.push(new XCCDFItemSelectUndoCommand(this, curr, checkState));
        }

        for (int i = 0; i < curr->childCount(); ++i)
            stack.push(curr->child(i));
    }

    mUndoStack.endMacro();
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

struct xccdf_item* TailoringWindow::getXCCDFItemById(const QString& id) const
{
    return xccdf_benchmark_get_item(mBenchmark, id.toUtf8().constData());
}

void TailoringWindow::changeSelectionToXCCDFItemById(const QString& id)
{
    QList<QTreeWidgetItem*> matches = mUI.itemsTree->findItems(id, Qt::MatchContains | Qt::MatchRecursive, 1);
    for (QList<QTreeWidgetItem*>::const_iterator it = matches.constBegin();
         it != matches.constEnd(); ++it)
    {
        struct xccdf_item* item = getXccdfItemFromTreeItem(*it);
        const QString itemId = QString::fromUtf8(xccdf_item_get_id(item));

        if (id != itemId)
            continue;

        mUI.itemsTree->setCurrentItem(*it);
        break;
    }
}

QString TailoringWindow::getCurrentValueValue(struct xccdf_value* xccdfValue)
{
    return QString::fromUtf8(xccdf_policy_get_value_of_item(mPolicy, xccdf_value_to_item(xccdfValue)));
}

void TailoringWindow::setValueValueWithUndoCommand(struct xccdf_value* xccdfValue, const QString& newValue)
{
    mUndoStack.push(new XCCDFValueChangeUndoCommand(this, xccdfValue, newValue, getCurrentValueValue(xccdfValue)));
}

const std::vector<struct xccdf_rule*>& TailoringWindow::getRulesAffectedByValue(struct xccdf_value* xccdfValue) const
{
    static std::vector<struct xccdf_rule*> empty;

    ValueAffectsRulesMap::const_iterator it = mValueAffectsRulesMap.find(xccdfValue);
    if (it != mValueAffectsRulesMap.end())
        return it->second;

    return empty;
}

void TailoringWindow::deselectAllChildrenItems()
{
    createSelectionMacro(mBenchmarkItem, false, QObject::tr("Deselect All"));
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

    synchronizeProfileItem();
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
        QMessageBox msgBox(this);
        msgBox.setIcon(QMessageBox::Question);
        msgBox.setStandardButtons(QMessageBox::Yes | QMessageBox::No);
        if (mNewProfile)
        {
            msgBox.setWindowTitle("Confirm delete profile?");
            msgBox.setText(QObject::tr("Are you sure you want to discard all changes performed in this tailoring window and delete the profile?"));
            msgBox.button(QMessageBox::Yes)->setText(QObject::tr("Delete profile"));
            msgBox.button(QMessageBox::No)->setText(QObject::tr("Don't delete profile"));
        }
        else
        {
            msgBox.setWindowTitle("Confirm discard of changes?");
            msgBox.setText(QObject::tr("Are you sure you want to discard all changes performed in this tailoring window?"));
            msgBox.button(QMessageBox::Yes)->setText(QObject::tr("Discard"));
            msgBox.button(QMessageBox::No)->setText(QObject::tr("Don't discard"));
        }
        msgBox.setDefaultButton(QMessageBox::No);

        // Setting dialogbuttonbox-buttons-have-icons to 0 should remove the icons of the
        // dialog button, but it's not working.
        // Setting icon-size of the buttons to 0 works for now
        msgBox.setStyleSheet("QPushButton {icon-size: 0px 0px}");

        if (msgBox.exec() == QMessageBox::No)
        {
            event->ignore();
            return;
        }

        // undo everything
        mUndoStack.setIndex(0);
        // TODO: Delete the profile if it was created as a tailoring action
    }

    serializeCollapsedItems();
    removeOldCollapsedLists();

    QMainWindow::closeEvent(event);

    // TODO: This is the only place where we depend on MainWindow which really sucks
    //       and makes this code more spaghetti-fied. Ideally MainWindow would handle
    //       this connection but there are no signals for window closure, the only
    //       way to react is to reimplement closeEvent... This needs further research.

    if (mParentMainWindow)
    {
        mParentMainWindow->notifyTailoringFinished(mNewProfile, mChangesConfirmed);
#ifndef _WIN32
        // enabling main window like this on Windows causes workbench to hang

        // calling the slot forces Qt to call it when it enters the MainWindow event loop
        // the time delay doesn't really matter
        QTimer::singleShot(0, mParentMainWindow, SLOT(enable()));
#endif
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
    {
        mQSettings->remove(getQSettingsKey());
        mQSettings->remove(getQSettingsKey() + "_lastUsed");
    }
    else
    {
        mQSettings->setValue(getQSettingsKey(), QVariant(mCollapsedItemIds.toList()));
        mQSettings->setValue(getQSettingsKey() + "_lastUsed", QVariant(QDateTime::currentDateTime()));
    }
}

void TailoringWindow::removeOldCollapsedLists()
{
    const int maxAgeInDays = 3 * 31; // ~3 months should be enough for everyone :-P
    const QDateTime currentDateTime = QDateTime::currentDateTime();

    QStringList keys = mQSettings->childKeys();
    for (QStringList::const_iterator it = keys.constBegin(); it != keys.constEnd(); ++it)
    {
        const QString& key = *it;
        if (!key.startsWith("collapsed_items_") || key.endsWith("_lastUsed"))
            continue;

        const QString lastUsedKey = key + "_lastUsed";
        const QVariant keyDateTimeVariant = mQSettings->value(lastUsedKey);
        // mercilessly remove if no last used date time is available
        if (keyDateTimeVariant.isNull())
            mQSettings->remove(key);

        const QDateTime keyDateTime = keyDateTimeVariant.toDateTime();
        if (keyDateTime.daysTo(currentDateTime) > maxAgeInDays)
        {
            mQSettings->remove(key);
            mQSettings->remove(lastUsedKey);
        }
    }
}

void TailoringWindow::syncCollapsedItems()
{
    QSet<QString> usedCollapsedItems;
    syncCollapsedItem(mBenchmarkItem, usedCollapsedItems);
    // This "cleans" the ids of non-existent ones.
    // That's useful when the content changes and avoids cruft buildup in the settings files.
    mCollapsedItemIds = usedCollapsedItems;
}

void TailoringWindow::syncCollapsedItem(QTreeWidgetItem* item, QSet<QString>& usedCollapsedIds)
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(item);
    const QString id = QString::fromUtf8(xccdf_item_get_id(xccdfItem));
    
    for (int i = 0; i < item->childCount(); ++i)
        syncCollapsedItem(item->child(i), usedCollapsedIds);

    if (mCollapsedItemIds.contains(id))
    {
        mUI.itemsTree->collapseItem(item);
        usedCollapsedIds.insert(id);
    }
    else
    {
        mUI.itemsTree->expandItem(item);
    }
}

void TailoringWindow::createTreeItem(QTreeWidgetItem* treeItem, struct xccdf_item* xccdfItem)
{
    ++mSynchronizeItemLock;

    const QString title = oscapItemGetReadableTitle(xccdfItem, mPolicy);
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
            treeItem->setFlags(treeItem->flags() | Qt::ItemIsUserCheckable);
            break;
        case XCCDF_VALUE:
            treeItem->setFlags(treeItem->flags() & ~Qt::ItemIsUserCheckable);
            break;
        default:
            break;
    }

    typedef std::vector<struct xccdf_item*> XCCDFItemVector;

    XCCDFItemVector itemsToAdd;

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

    unsigned int idx = 0;
    for (XCCDFItemVector::const_iterator it = itemsToAdd.begin();
            it != itemsToAdd.end(); ++it, ++idx)
    {
        struct xccdf_item* childXccdfItem = *it;
        QTreeWidgetItem* childTreeItem = 0;

        childTreeItem = new QTreeWidgetItem();

        childTreeItem->setFlags(
                Qt::ItemIsSelectable |
                Qt::ItemIsEnabled);

        treeItem->insertChild(idx, childTreeItem);

        createTreeItem(childTreeItem, childXccdfItem);
    }

    --mSynchronizeItemLock;
}

void TailoringWindow::generateValueAffectsRulesMap(struct xccdf_item* item)
{
    struct xccdf_item_iterator* items = 0;

    switch (xccdf_item_get_type(item))
    {
        case XCCDF_BENCHMARK:
            items = xccdf_benchmark_get_content(xccdf_item_to_benchmark(item));
            break;

        case XCCDF_GROUP:
            items = xccdf_group_get_content(xccdf_item_to_group(item));
            break;

        case XCCDF_RULE:
            {
                struct xccdf_check_iterator* checks = xccdf_rule_get_checks(xccdf_item_to_rule(item));
                while (xccdf_check_iterator_has_more(checks))
                {
                    struct xccdf_check* check = xccdf_check_iterator_next(checks);
                    struct xccdf_check_export_iterator* checkExports = xccdf_check_get_exports(check);
                    while (xccdf_check_export_iterator_has_more(checkExports))
                    {
                        struct xccdf_check_export* checkExport = xccdf_check_export_iterator_next(checkExports);
                        const QString valueId = QString::fromUtf8(xccdf_check_export_get_value(checkExport));
                        struct xccdf_item* value = getXCCDFItemById(valueId);

                        if (xccdf_item_get_type(value) != XCCDF_VALUE)
                        {
                            // TODO: We expected xccdf value but got something else, warn about this?
                            continue;
                        }

                        mValueAffectsRulesMap[xccdf_item_to_value(value)].push_back(xccdf_item_to_rule(item));
                    }
                    xccdf_check_export_iterator_free(checkExports);
                }
                xccdf_check_iterator_free(checks);
            }
            break;

        default:
            // noop
            break;
    }

    if (items)
    {
        while (xccdf_item_iterator_has_more(items))
        {
            generateValueAffectsRulesMap(xccdf_item_iterator_next(items));
        }
        xccdf_item_iterator_free(items);
    }
}

void TailoringWindow::searchNext()
{
    const QString& needle = mSearchBox->text();

    // makes no sense to search for empty strings
    if (needle.isEmpty())
    {
        mSearchFeedback->setText("");
        return;
    }

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

        if (!match->isDisabled())
            mUI.itemsTree->setCurrentItem(match);
        else
        {
            // We cannot use setCurrentItem() on disabled items
            // so we will use a workaround

            QTreeWidgetItem * dummyItem = mUI.itemsTree->currentItem();

            // Setting of "new" current item cause removing selection
            // from rest of items
            mUI.itemsTree->setCurrentItem(dummyItem);

            // and we will remove selection from current item, too.
            dummyItem->setSelected(false);

            // Emulate setting of "currentItem"
            match->setSelected(true);
            mUI.itemsTree->scrollToItem(match);
            emit itemSelectionChanged(match, NULL);
        }

        mSearchBox->setStyleSheet("");
        mSearchFeedback->setText(QObject::tr("Showing match %1 out of %2 total found.").arg(mSearchSkippedItems + 1).arg(matches.size()));
    }
    else
    {
        mSearchSkippedItems = 0;
        // In case of no match we intentionally do not change selection
        mSearchBox->setStyleSheet("background: #f66");
        mSearchFeedback->setText(QObject::tr("No matches found."));
    }
}

void TailoringWindow::itemSelectionChanged(QTreeWidgetItem* current, QTreeWidgetItem* previous)
{
    struct xccdf_item* item = getXccdfItemFromTreeItem(current);
    setUpdatesEnabled(false);
    if (item)
    {
        mItemPropertiesDockWidget->setXccdfItem(item, mPolicy);
        mItemPropertiesDockWidget->show();
        mProfilePropertiesDockWidget->hide();
    }
    else
    {
        mItemPropertiesDockWidget->setXccdfItem(0, mPolicy);
        mItemPropertiesDockWidget->hide();
        mProfilePropertiesDockWidget->show();
    }
    setUpdatesEnabled(true);
}

void TailoringWindow::itemChanged(QTreeWidgetItem* treeItem, int column)
{
    if (mSynchronizeItemLock > 0)
        return;

    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(treeItem);
    if (!xccdfItem)
        return;

    if (xccdf_item_get_type(xccdfItem) == XCCDF_VALUE)
        return;

    const bool checkState = treeItem->checkState(0) == Qt::Checked;

    if (xccdf_item_get_type(xccdfItem) == XCCDF_GROUP)
    {
        const QString title = oscapItemGetReadableTitle(xccdfItem, mPolicy);
        createSelectionMacro(treeItem, checkState, checkState ? QObject::tr("Select Group \"%1\"").arg(title) : QObject::tr("Deselect Group \"%1\"").arg(title));
    }
    else
    {
        mUndoStack.push(new XCCDFItemSelectUndoCommand(this, treeItem, checkState));
    }
}

void TailoringWindow::itemExpanded(QTreeWidgetItem* item)
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(item);
    if (!xccdfItem)
        return;

    const QString id = QString::fromUtf8(xccdf_item_get_id(xccdfItem));
    mCollapsedItemIds.remove(id);
}

void TailoringWindow::itemCollapsed(QTreeWidgetItem* item)
{
    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(item);
    if (!xccdfItem)
        return;

    const QString id = QString::fromUtf8(xccdf_item_get_id(xccdfItem));
    mCollapsedItemIds.insert(id);
}
