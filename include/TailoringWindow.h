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

#include <QMainWindow>
#include <QSettings>
#include <QUndoStack>

extern "C"
{
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
}

#include "ui_TailoringWindow.h"
#include "ui_ProfilePropertiesDockWidget.h"
#include "ui_XCCDFItemPropertiesDockWidget.h"

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
        static struct xccdf_item* getXccdfItemFromTreeItem(QTreeWidgetItem* treeItem);

        /**
         * @param newProfile whether the profile in policy was created solely for tailoring
         */
        TailoringWindow(struct xccdf_policy* policy, struct xccdf_benchmark* benchmark, bool newProfile, MainWindow* parent = 0);
        virtual ~TailoringWindow();

        /**
         * @brief Makes sure that given XCCDF item is selected or deselected in the policy and profile
         *
         * This method adds a new select to the policy and profile. This select overrides all
         * previous selects if any.
         */
        void setItemSelected(struct xccdf_item* xccdfItem, bool selected);

        /**
         * @brief Synchronizes the profile item with the profile
         */
        void synchronizeProfileItem();

        void setValueValue(struct xccdf_value* xccdfValue, const QString& newValue);
        void refreshXccdfItemPropertiesDockWidget();

        struct xccdf_item* getXCCDFItemById(const QString& id) const;

        void changeSelectionToXCCDFItemById(const QString& id);

        QString getCurrentValueValue(struct xccdf_value* xccdfValue);
        void setValueValueWithUndoCommand(struct xccdf_value* xccdfValue, const QString& newValue);

        const std::vector<struct xccdf_rule*>& getRulesAffectedByValue(struct xccdf_value* xccdfValue) const;

    public slots:
        /**
         * @brief Traverses the tree into all selected groups and deselects all their items
         */
        void deselectAllChildrenItems();

    public:

        /**
         * @brief Retrieves ID of profile that is being tailored (in suitable language)
         */
        QString getProfileID() const;

        /**
         * @brief Goes through profile title texts and sets one of them to given title
         *
         * @see TailoringWindow::setProfileTitleWithUndoCommand
         */
        void setProfileTitle(const QString& title);

        /**
         * @brief Retrieves title of profile that is being tailoring (in suitable language)
         */
        QString getProfileTitle() const;

        /**
         * @brief Creates a new undo command that changes title of tailored profile and pushes it onto the undo stack
         *
         * @see TailoringWindow::setProfileTitle
         */
        void setProfileTitleWithUndoCommand(const QString& newTitle);

        /**
         * @brief Goes through profile description texts and sets one of them to given title
         *
         * @see TailoringWindow::setProfileDescriptionWithUndoCommand
         */
        void setProfileDescription(const QString& description);

        /**
         * @brief Retrieves description of profile that is being tailoring (in suitable language)
         */
        QString getProfileDescription() const;

        /**
         * @brief Retrieves readable title of given XCCDF item [in HTML]
         *
         * @internal This method performs substitution using mPolicy
         */
        QString getXCCDFItemTitle(struct xccdf_item* item) const;

        /**
         * @brief Retrieves readable description of given XCCDF item [in HTML]
         *
         * @internal This method performs substitution using mPolicy
         */
        QString getXCCDFItemDescription(struct xccdf_item* item) const;

        /**
         * @brief Creates a new undo command that changes description of tailored profile and pushes it onto the undo stack
         *
         * @see TailoringWindow::setProfileDescription
         */
        void setProfileDescriptionWithUndoCommand(const QString& newDescription);

        /**
         * @brief Refreshes profile properties dock widget to accurately represent tailored profile
         */
        void refreshProfileDockWidget();

    public slots:
        void confirmAndClose();
        void deleteProfileAndDiscard();

    protected:
        /// Reimplemented to refresh profiles and selected rules in the parent main window
        virtual void closeEvent(QCloseEvent* event);

    private:
        QString getQSettingsKey() const;
        void deserializeCollapsedItems();
        void serializeCollapsedItems();

        /// Internal usage only, this method assumes serializeCollapsedItems was called recently
        void removeOldCollapsedLists();

        void syncCollapsedItems();
        void syncCollapsedItem(QTreeWidgetItem* item, QSet<QString>& usedCollapsedIds);

        void createTreeItem(QTreeWidgetItem* treeItem, struct xccdf_item* xccdfItem);
        void synchronizeTreeItemSelections(QTreeWidgetItem *treeItem);
        
        void createSelectionMacro(QTreeWidgetItem* treeItem, bool checkState, const QString& commandName);

        MainWindow* mParentMainWindow;
        /// Used to remember manually collapsed items for a particular item
        QSet<QString> mCollapsedItemIds;
        /// Used to serialize manually collapsed items between scap-workbench runs
        QSettings* mQSettings;

        /// if > 0, ignore itemChanged signals, these would just excessively add selects and bloat memory
        unsigned int mSynchronizeItemLock;

        /// UI designed in Qt Designer
        Ui_TailoringWindow mUI;

        /// The root profile item in the tree (profile isn't an xccdf_item!)
        QTreeWidgetItem* mProfileItem;
        /// The root benchmark item in the tree
        QTreeWidgetItem* mBenchmarkItem;

        XCCDFItemPropertiesDockWidget* mItemPropertiesDockWidget;
        ProfilePropertiesDockWidget* mProfilePropertiesDockWidget;
        QDockWidget* mUndoViewDockWidget;

        QLineEdit* mSearchBox;
        QPushButton* mSearchButton;
        QLabel* mSearchFeedback;

        struct xccdf_policy* mPolicy;
        struct xccdf_profile* mProfile;
        struct xccdf_benchmark* mBenchmark;

        QUndoStack mUndoStack;

        bool mNewProfile;
        bool mChangesConfirmed;

        unsigned int mSearchSkippedItems;
        QString mSearchCurrentNeedle;

        void generateValueAffectsRulesMap(struct xccdf_item* item);

        typedef std::map<struct xccdf_value*, std::vector<struct xccdf_rule*> > ValueAffectsRulesMap;
        ValueAffectsRulesMap mValueAffectsRulesMap;
        
        QAction* mDeselectAllAction;

    private slots:
        void searchNext();
        void synchronizeTreeItem();
        void itemSelectionChanged(QTreeWidgetItem* current, QTreeWidgetItem* previous);
        void itemChanged(QTreeWidgetItem* item, int column);
        void itemExpanded(QTreeWidgetItem* item);
        void itemCollapsed(QTreeWidgetItem* item);
};

#endif
