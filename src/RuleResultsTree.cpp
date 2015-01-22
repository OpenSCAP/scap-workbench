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

    mUI.ruleTree->header()->setResizeMode(0, QHeaderView::Stretch);

    QObject::connect(
        mUI.ruleTree, SIGNAL(itemExpanded(QTreeWidgetItem*)),
        this, SLOT(updateDescriptionForItem(QTreeWidgetItem*))
    );
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
    // clear all items
    mUI.ruleTree->clear();
    mRuleIdToTreeItemMap.clear();

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

    mUI.ruleTree->setUpdatesEnabled(false);

    // we filter through a set to avoid duplicates and get a sensible ordering
    for (std::vector<struct xccdf_rule*>::const_iterator it = selectedRules.begin();
         it != selectedRules.end(); ++it)
    {
        struct xccdf_rule* rule = *it;

        const QString ruleID = QString::fromUtf8(xccdf_rule_get_id(rule));

        QTreeWidgetItem* treeItem = new QTreeWidgetItem();
        treeItem->setText(0, oscapItemGetReadableTitle(xccdf_rule_to_item(rule), policy));

        QTreeWidgetItem* descriptionItem = new QTreeWidgetItem();
        descriptionItem->setData(0, Qt::UserRole, QVariant::fromValue(oscapItemGetReadableDescription(xccdf_rule_to_item(rule), policy)));
        treeItem->addChild(descriptionItem);

        mUI.ruleTree->addTopLevelItem(treeItem);
        mRuleIdToTreeItemMap[ruleID] = treeItem;
    }

    mUI.ruleTree->setUpdatesEnabled(true);
}

unsigned int RuleResultsTree::getSelectedRulesCount()
{
    // assumes that ruleTree is in a refreshed state
    return mUI.ruleTree->topLevelItemCount();
}

void RuleResultsTree::clearResults()
{
    mUI.ruleTree->setUpdatesEnabled(false);

    for (RuleIdToTreeItemMap::iterator it = mRuleIdToTreeItemMap.begin();
         it != mRuleIdToTreeItemMap.end(); ++it)
    {
        // by injecting empty results we clear the previous ones
        injectRuleResult(it->first, "");
    }

    mUI.ruleTree->setUpdatesEnabled(true);
}

bool RuleResultsTree::hasRuleResult(const QString& ruleID) const
{
    RuleIdToTreeItemMap::const_iterator it = mRuleIdToTreeItemMap.find(ruleID);
    if (it == mRuleIdToTreeItemMap.end())
        return false;

    const QTreeWidgetItem* item = it->second;
    return !item->text(1).isEmpty();
}

void RuleResultsTree::injectRuleResult(const QString& ruleID, const QString& result)
{
    QString resultTooltip;
    QBrush resultBrush;
    if (result.isEmpty())
    {
        resultBrush.setColor(Qt::transparent);
        resultTooltip = "";
    }
    else if (result == "processing")
    {
        resultBrush.setColor(Qt::darkYellow);
        resultTooltip = QObject::tr("This rule is currently being processed.");
    }
    else if (result == "pass")
    {
        resultBrush.setColor(Qt::darkGreen);
        resultTooltip = QObject::tr("The target system or system component satisfied all the conditions of this rule.");
    }
    else if (result == "fail")
    {
        resultBrush.setColor(Qt::red);
        resultTooltip = QObject::tr("The target system or system component did not satisfy every condition of this rule.");
    }
    else if (result == "error")
    {
        resultBrush.setColor(Qt::red);
        resultTooltip = QObject::tr("The checking engine could not complete the evaluation, therefore the status of the target's "
                "compliance with the rule is not certain. This could happen, for example, if a testing "
                "tool was run with insufficient privileges and could not gather all of the necessary information.");
    }
    else if (result == "unknown")
    {
        resultBrush.setColor(Qt::darkGray);
        resultTooltip = QObject::tr("The testing tool encountered some problem and the result is unknown.");
    }
    else if (result == "notapplicable")
    {
        resultBrush.setColor(Qt::darkGray);
        resultTooltip = QObject::tr("The rule was not applicable to the target machine of the test. For example, the "
                "rule might have been specific to a different version of the target OS, or it might "
                "have been a test against a platform feature that was not installed.");
    }
    else if (result == "notchecked")
    {
        resultBrush.setColor(Qt::darkGray);
        resultTooltip = QObject::tr("The rule was not evaluated by the checking engine. There were no check elements "
                "inside the rule or none of the check systems of the check elements were supported.");
    }
    else if (result == "notselected")
    {
        resultBrush.setColor(Qt::darkGray);
        resultTooltip = QObject::tr("The rule was not selected in the benchmark.");
    }
    else if (result == "informational")
    {
        resultBrush.setColor(Qt::darkGray);
        resultTooltip = QObject::tr("The rule was checked, but the output from the checking engine is simply "
                "information for auditors or administrators; it is not a compliance category.");
    }
    else if (result == "fixed")
    {
        resultBrush.setColor(Qt::darkGreen);
        resultTooltip = QObject::tr("The rule had failed, but was then fixed (most probably using remediation).");
    }
    else
        resultBrush.setColor(Qt::darkGray);

    QTreeWidgetItem* treeItem = mRuleIdToTreeItemMap[ruleID];
    if (!treeItem)
        throw RuleResultsTreeException(
            QString("Could not find rule of ID '%1'. Result of this rule was '%2' but it can't be reported! "
                    "This could be a difference between remote and local openscap versions or a bug in "
                    "workbench.").arg(ruleID, result)
        );

    treeItem->setText(1, result);
    treeItem->setToolTip(1, resultTooltip);
    treeItem->setForeground(1, resultBrush);

    // Highlight currently processed rule
    QBrush backgroundBrush(Qt::NoBrush);
    if (result == "processing")
        backgroundBrush = QBrush(Qt::lightGray);
    treeItem->setBackground(0, backgroundBrush);
    treeItem->setBackground(1, backgroundBrush);

    if (!result.isEmpty())
    {
        // ensure the updated item is visible
        mUI.ruleTree->scrollToItem(treeItem);
    }
}

void RuleResultsTree::prepareForScanning()
{}

void RuleResultsTree::updateDescriptionForItem(QTreeWidgetItem* item)
{
    if (!item)
        return;

    QTreeWidgetItem* descriptionItem = item->child(0);
    if (mUI.ruleTree->itemWidget(descriptionItem, 0))
        return;

    mUI.ruleTree->setUpdatesEnabled(false);

    const QString description = descriptionItem->data(0, Qt::UserRole).toString();
    QLabel* descriptionWidget = new QLabel(description, mUI.ruleTree);
    descriptionWidget->setWordWrap(true);
    descriptionWidget->setTextFormat(Qt::RichText);
    mUI.ruleTree->setItemWidget(descriptionItem, 0, descriptionWidget);

    mUI.ruleTree->setUpdatesEnabled(true);
}
