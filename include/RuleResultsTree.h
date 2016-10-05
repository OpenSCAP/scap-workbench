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

#ifndef SCAP_WORKBENCH_RULE_RESULTS_TREE_H_
#define SCAP_WORKBENCH_RULE_RESULTS_TREE_H_

#include "ForwardDecls.h"
#include <QWidget>

#include "ui_RuleResultsTree.h"

/**
 * @brief GUI element that shows both currently selected rules and their results
 *
 * At first glance it might seem odd that a single widget has these two responsibilities,
 * but from a UX standapoint it makes sense. It allows for useful features - users can
 * browse descriptions while scan is underway. The state of expanded/collapsed descriptions
 * is persisted even after scan finishes.
 */
class RuleResultsTree : public QWidget
{
    Q_OBJECT

    public:
        explicit RuleResultsTree(QWidget* parent = 0);
        virtual ~RuleResultsTree();

        /**
         * @brief Sets the state of the tree to be consistent with rules selected
         *
         * @param scanningSession Session from which we will determine which rules are selected
         */
        void refreshSelectedRules(ScanningSession* scanningSession);

        /**
         * @brief How many rules does RuleResultTree think are selected?
         *
         * Current implementation returns the amount of top-level items in the tree widget.
         */
        unsigned int getSelectedRulesCount();

        /**
         * @brief If any results are recorded for any rules, this method purges them - sets them to ""
         */
        void clearResults();

        /**
         * @brief Do we have a record of a valid result for given ruleID
         *
         * Valid result means something other than empty. Even "fail" rules are valid results
         * in this context!
         */
        bool hasRuleResult(const QString& ruleID) const;

        /**
         * @brief Records given result for given rule ID
         *
         * This is called from the MainWindow as results are gathered for more and more rules.
         *
         * @note
         * Passing "" as result clears the previous result, hasRuleResult(ruleID) will return
         * false after you inject "" result.
         *
         * @see RuleResultTree::clearResults
         */
        void injectRuleResult(const QString& ruleID, const QString& result);

        /**
         * Reserved method to prepare RuleResultsTree for scanning.
         *
         * This may do something useful or fancy in the future. Right now it does nothing.
         */
        void prepareForScanning();

        /**
         * @brief Toggles expanded/collapsed state of RuleResults
         */
        void toggleAllRuleResultDescription(bool checked);

    public slots:
        /**
         * @brief Checks if all RuleResults are expanded or collapsed
         *
         * If all RuleResults are expanded or collapsed allRuleResultsExpanded signal
         * is emitted.
         */
        void checkRuleResultsExpanded(bool lastAction);

    signals:
        /**
         * @brief This is signaled when all RuleResults are either expanded or collapsed
         *
         * We signal this when a RuleResult has been expanded or collapse by user click
         * and as a result all RuleResults are now expanded or collapsed.
         */
        void allRuleResultsExpanded(bool checked);

    private:
        void clearAllItems();

        Ui_RuleResultsTree mUI;
        QVBoxLayout* mInternalLayout;

        typedef std::map<QString, RuleResultItem*> RuleIdToWidgetItemMap;
        /// A map to get tree widget items for given rule IDs, refreshSelectedRules changes this
        RuleIdToWidgetItemMap mRuleIdToWidgetItemMap;
};

#endif
