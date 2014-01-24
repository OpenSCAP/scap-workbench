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
#include "APIHelpers.h"

#include <set>
#include <cassert>

ProfilePropertiesDockWidget::ProfilePropertiesDockWidget(TailoringWindow* window, QWidget* parent):
    QDockWidget(parent),

    mRefreshInProgress(false),
    mWindow(window)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.title, SIGNAL(textChanged(const QString&)),
        this, SLOT(profileTitleChanged(const QString&))
    );

    QObject::connect(
        mUI.description, SIGNAL(textChanged()),
        this, SLOT(profileDescriptionChanged())
    );
}

ProfilePropertiesDockWidget::~ProfilePropertiesDockWidget()
{}

void ProfilePropertiesDockWidget::refresh()
{
    if (mUI.id->text() != mWindow->getProfileID())
        mUI.id->setText(mWindow->getProfileID());

    if (mUI.title->text() != mWindow->getProfileTitle())
    {
        // This prevents a new undo command being spawned as a result of refreshing
        mRefreshInProgress = true;
        mUI.title->setText(mWindow->getProfileTitle());
        mRefreshInProgress = false;
    }

    if (mUI.description->toPlainText() != mWindow->getProfileDescription())
    {
        // This prevents a new undo command being spawned as a result of refreshing
        mRefreshInProgress = true;
        mUI.description->setPlainText(mWindow->getProfileDescription());
        mRefreshInProgress = false;
    }
}

void ProfilePropertiesDockWidget::profileTitleChanged(const QString& newTitle)
{
    if (mRefreshInProgress)
        return;

    mWindow->setProfileTitleWithUndoCommand(newTitle);
}

void ProfilePropertiesDockWidget::profileDescriptionChanged()
{
    if (mRefreshInProgress)
        return;

    mWindow->setProfileDescriptionWithUndoCommand(mUI.description->toPlainText());
}

XCCDFItemPropertiesDockWidget::XCCDFItemPropertiesDockWidget(QWidget* parent):
    QDockWidget(parent),

    mXccdfItem(0)
{
    mUI.setupUi(this);
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
        mUI.titleLineEdit->setText(oscapTextIteratorGetPreferred(xccdf_item_get_title(mXccdfItem)));
        mUI.idLineEdit->setText(QString::fromUtf8(xccdf_item_get_id(mXccdfItem)));
        mUI.descriptionTextEdit->setHtml(oscapTextIteratorGetPreferred(xccdf_item_get_description(mXccdfItem)));
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

ProfileTitleChangeUndoCommand::ProfileTitleChangeUndoCommand(TailoringWindow* window, const QString& oldTitle, const QString& newTitle):
    mWindow(window),
    mOldTitle(oldTitle),
    mNewTitle(newTitle)
{}

ProfileTitleChangeUndoCommand::~ProfileTitleChangeUndoCommand()
{}

int ProfileTitleChangeUndoCommand::id() const
{
    return 2;
}

void ProfileTitleChangeUndoCommand::redo()
{
    mWindow->setProfileTitle(mNewTitle);
    mWindow->refreshProfileDockWidget();
}

void ProfileTitleChangeUndoCommand::undo()
{
    mWindow->setProfileTitle(mOldTitle);
    mWindow->refreshProfileDockWidget();
}

bool ProfileTitleChangeUndoCommand::mergeWith(const QUndoCommand *other)
{
    if (other->id() != id())
        return false;

    mNewTitle = static_cast<const ProfileTitleChangeUndoCommand*>(other)->mNewTitle;
    return true;
}
ProfileDescriptionChangeUndoCommand::ProfileDescriptionChangeUndoCommand(TailoringWindow* window, const QString& oldDesc, const QString& newDesc):
    mWindow(window),
    mOldDesc(oldDesc),
    mNewDesc(newDesc)
{}

ProfileDescriptionChangeUndoCommand::~ProfileDescriptionChangeUndoCommand()
{}

int ProfileDescriptionChangeUndoCommand::id() const
{
    return 3;
}

void ProfileDescriptionChangeUndoCommand::redo()
{
    mWindow->setProfileDescription(mNewDesc);
    mWindow->refreshProfileDockWidget();
}

void ProfileDescriptionChangeUndoCommand::undo()
{
    mWindow->setProfileDescription(mOldDesc);
    mWindow->refreshProfileDockWidget();
}

bool ProfileDescriptionChangeUndoCommand::mergeWith(const QUndoCommand *other)
{
    if (other->id() != id())
        return false;

    mNewDesc = static_cast<const ProfileDescriptionChangeUndoCommand*>(other)->mNewDesc;
    return true;
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

TailoringWindow::TailoringWindow(struct xccdf_policy* policy, struct xccdf_benchmark* benchmark, MainWindow* parent):
    QMainWindow(parent),

    mParentMainWindow(parent),

    mSynchronizeItemLock(0),

    mProfilePropertiesDockWidget(new ProfilePropertiesDockWidget(this, this)),
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

    addDockWidget(Qt::RightDockWidgetArea, mProfilePropertiesDockWidget);
    addDockWidget(Qt::RightDockWidgetArea, mItemPropertiesDockWidget);

    {
        QAction* undoAction = mUndoStack.createUndoAction(this, "Undo");
        undoAction->setIcon(QIcon::fromTheme("edit-undo"));
        QAction* redoAction = mUndoStack.createRedoAction(this, "Redo");
        redoAction->setIcon(QIcon::fromTheme("edit-redo"));

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
    _refreshXCCDFItemChildrenDisabledState(benchmarkItem, true);

    // we cannot rely on any ordering from openscap, to make sure items appear
    // in the same order when scap-workbench is run multiple times we have to sort
    mUI.itemsTree->sortByColumn(0, Qt::AscendingOrder);

    // let title stretch and take space as the tailoring window grows
    mUI.itemsTree->header()->setResizeMode(0, QHeaderView::Stretch);

    mUI.itemsTree->expandAll();

    setWindowTitle(QString("Tailoring '%1'").arg(oscapTextIteratorGetPreferred(xccdf_profile_get_title(mProfile))));

    mProfilePropertiesDockWidget->refresh();
    mItemPropertiesDockWidget->refresh();

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

    treeItem->setText(0, oscapTextIteratorGetPreferred(xccdf_item_get_title(xccdfItem)));

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
        {
            treeItem->setCheckState(0,
                    getXccdfItemInternalSelected(mPolicy, xccdfItem) ? Qt::Checked : Qt::Unchecked);
            _syncXCCDFItemChildrenDisabledState(treeItem, treeItem->checkState(0));
            break;
        }
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

void TailoringWindow::refreshProfileDockWidget()
{
    mProfilePropertiesDockWidget->refresh();
}

void TailoringWindow::closeEvent(QCloseEvent * event)
{
    QMainWindow::closeEvent(event);

    // TODO: This is the only place where we depend on MainWindow which really sucks
    //       and makes this code more spaghetti-fied. Ideally MainWindow would handle
    //       this connection but there are no signals for window closure, the only
    //       way to react is to reimplement closeEvent... This needs further research.

    if (mParentMainWindow)
    {
        mParentMainWindow->refreshSelectedRulesTree();
        mParentMainWindow->refreshProfiles();
    }
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

    const bool checkState = treeItem->checkState(0) == Qt::Checked;

    struct xccdf_item* xccdfItem = getXccdfItemFromTreeItem(treeItem);
    if (!xccdfItem)
        return;

    const bool itemCheckState = getXccdfItemInternalSelected(mPolicy, xccdfItem);

    if (checkState != itemCheckState)
        mUndoStack.push(new XCCDFItemSelectUndoCommand(this, treeItem, checkState));

    _syncXCCDFItemChildrenDisabledState(treeItem, checkState);
}
