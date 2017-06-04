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

#include "RuleResultsTree.h"
#include "RuleResultItem.h"
#include "ScanningSession.h"
#include "APIHelpers.h"
#include "Exceptions.h"

#include <QLabel>

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
}

RuleResultsTree::RuleResultsTree(QWidget* parent):
    QWidget(parent)
{
    mUI.setupUi(this);

    mInternalLayout = new QVBoxLayout();
    mInternalLayout->setSpacing(0);
    mInternalLayout->setContentsMargins(4, 4, 4, 4);
    mUI.scrollAreaWidgetContents->setLayout(mInternalLayout);

    setFocusProxy(mUI.scrollArea);
}

RuleResultsTree::~RuleResultsTree()
{}

/*
Unfortunately, xccdf_policy won't let us see its "selected-final" hashmap.
Instead we have to gather all rules and for each rule ID we check the policy.
*/
inline void gatherAllSelectedRules(struct xccdf_policy* policy, struct xccdf_item* current,
    std::vector<struct xccdf_rule*>& result)
{
    if (xccdf_item_get_type(current) == XCCDF_RULE)
    {
        struct xccdf_rule* rule = xccdf_item_to_rule(current);
        const bool selected = xccdf_policy_is_item_selected(policy, xccdf_rule_get_id(rule));

        if (selected)
            result.push_back(rule);
    }
    else if (xccdf_item_get_type(current) == XCCDF_BENCHMARK ||
        xccdf_item_get_type(current) == XCCDF_GROUP)
    {
        struct xccdf_item_iterator* it = xccdf_item_get_content(current);
        while (xccdf_item_iterator_has_more(it))
        {
            struct xccdf_item* item = xccdf_item_iterator_next(it);
            gatherAllSelectedRules(policy, item, result);
        }
        xccdf_item_iterator_free(it);
    }
}

void RuleResultsTree::refreshSelectedRules(ScanningSession* scanningSession)
{
    clearAllItems();

    if (!scanningSession)
        return;

    if (!scanningSession->fileOpened())
        return;

    struct xccdf_session* session = scanningSession->getXCCDFSession();
    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);

    struct xccdf_benchmark* benchmark = 0;
    try
    {
        benchmark = xccdf_policy_model_get_benchmark(xccdf_session_get_policy_model(scanningSession->getXCCDFSession()));
    }
    catch (const std::exception& e)
    {
        // This is not a critical error, just quit
        // FIXME: We should display some sort of an error indicator though to get bug reports!
        return;
    }

    std::vector<struct xccdf_rule*> selectedRules;

    gatherAllSelectedRules(policy, xccdf_benchmark_to_item(benchmark), selectedRules);

    mUI.scrollArea->setUpdatesEnabled(false);

    // we filter through a set to avoid duplicates and get a sensible ordering
    for (std::vector<struct xccdf_rule*>::const_iterator it = selectedRules.begin();
         it != selectedRules.end(); ++it)
    {
        struct xccdf_rule* rule = *it;

        RuleResultItem* item = new RuleResultItem(rule, policy, mUI.scrollArea);

        QObject::connect(
            item, SIGNAL(ruleResultDescriptionToggled(bool)),
            this, SLOT(checkRuleResultsExpanded(bool))
        );

        const QString ruleID = QString::fromUtf8(xccdf_rule_get_id(rule));
        mRuleIdToWidgetItemMap[ruleID] = item;

        mInternalLayout->addWidget(item);
    }

    mInternalLayout->addStretch();

    mUI.scrollArea->setUpdatesEnabled(true);
}

unsigned int RuleResultsTree::getSelectedRulesCount()
{
    // assumes that we are in a refreshed state
    return mRuleIdToWidgetItemMap.size();
}

void RuleResultsTree::clearResults()
{
    mUI.scrollArea->setUpdatesEnabled(false);

    for (RuleIdToWidgetItemMap::iterator it = mRuleIdToWidgetItemMap.begin();
         it != mRuleIdToWidgetItemMap.end(); ++it)
    {
        // by injecting empty results we clear the previous ones
        injectRuleResult(it->first, "");
    }

    mUI.scrollArea->setUpdatesEnabled(true);
}

bool RuleResultsTree::hasRuleResult(const QString& ruleID) const
{
    RuleIdToWidgetItemMap::const_iterator it = mRuleIdToWidgetItemMap.find(ruleID);
    if (it == mRuleIdToWidgetItemMap.end())
        return false;

    const RuleResultItem* item = it->second;
    return item->hasRuleResult();
}

void RuleResultsTree::injectRuleResult(const QString& ruleID, const QString& result)
{
    RuleResultItem* item = mRuleIdToWidgetItemMap[ruleID];
    if (!item)
        throw RuleResultsTreeException(
            QString("Could not find rule of ID '%1'. Result of this rule was '%2' but it can't be reported! "
                    "This could be a difference between remote and local openscap versions or a bug in "
                    "workbench.").arg(ruleID, result)
        );

    item->setRuleResult(result);

    if (!result.isEmpty())
    {
        // ensure the updated item is visible
        mUI.scrollArea->ensureWidgetVisible(item);
    }
}

void RuleResultsTree::prepareForScanning()
{}

void RuleResultsTree::toggleAllRuleResultDescription(bool checked)
{
    mUI.scrollArea->setUpdatesEnabled(false);

    for (RuleIdToWidgetItemMap::iterator it = mRuleIdToWidgetItemMap.begin();
         it != mRuleIdToWidgetItemMap.end(); ++it)
    {
        RuleResultItem* item = it->second;
        item->setRuleResultChecked(checked);
    }

    mUI.scrollArea->setUpdatesEnabled(true);
}

void RuleResultsTree::checkRuleResultsExpanded(bool lastAction)
{
    RuleResultItem* item;

    mUI.scrollArea->setUpdatesEnabled(false);

    RuleIdToWidgetItemMap::iterator it = mRuleIdToWidgetItemMap.begin();
    while (it != mRuleIdToWidgetItemMap.end())
    {
        item = it->second;
        if (lastAction == item->isChecked())
            ++it;
        else
        {
            mUI.scrollArea->setUpdatesEnabled(true);
            return;
        }
    }
    emit allRuleResultsExpanded(lastAction);

    mUI.scrollArea->setUpdatesEnabled(true);

}

void RuleResultsTree::clearAllItems()
{
    for (RuleIdToWidgetItemMap::const_iterator it = mRuleIdToWidgetItemMap.begin();
         it != mRuleIdToWidgetItemMap.end(); ++it)
    {
        delete it->second;
    }

    // remove the rest from the layout - spacers
    QLayoutItem* child;
    while ((child = mInternalLayout->takeAt(0)) != 0)
        delete child;

    mRuleIdToWidgetItemMap.clear();
}
