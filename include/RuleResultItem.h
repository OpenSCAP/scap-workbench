/*
 * Copyright 2015 Red Hat Inc., Durham, North Carolina.
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

#ifndef SCAP_WORKBENCH_RULE_RESULTS_ITEM_H_
#define SCAP_WORKBENCH_RULE_RESULTS_ITEM_H_

#include <QWidget>
#include "ui_RuleResultItem.h"

class RuleResultItem : public QWidget
{
    Q_OBJECT

    public:
        explicit RuleResultItem(struct xccdf_rule* rule, struct xccdf_policy* policy, QWidget* parent = 0);
        virtual ~RuleResultItem();

        void setRuleResult(const QString& result);
        bool hasRuleResult() const;

        void setRuleResultChecked(bool checked);

        bool isChecked();

    signals:
        void ruleResultDescriptionToggled(bool checked);

    private slots:
        void showDescriptionToggled(bool checked);

    private:
        Ui_RuleResultItem mUi;
        QString mDescriptionHTML;
};

#endif
